# core/utils/pl.py
from datetime import date, timedelta
from django.db.models import Sum, Q
from typing import Dict
from django.db.models.functions import Coalesce
from core.models import (
	Reservation, ReservationCast, ReservationCharge,
	CastRate, DriverRate, ShiftAttendance, DriverShift,
	RankCourse, CastCoursePrice, Payment, ManualEntry,
	ExpenseEntry
)
from decimal import Decimal
from calendar import monthrange
from datetime import date as dt



# ───────── 素コース価格を返す ─────────
def _base_course_price(rc: ReservationCast) -> int:
	"""
	rc: ReservationCast インスタンス
	優先順:
	  1) CastCoursePrice (キャスト個別価格)
	  2) RankCourse	 (店舗ランク標準価格)
	"""
	# ① キャスト個別
	ccp = (
		CastCoursePrice.objects
		.filter(cast_profile=rc.cast_profile, course=rc.course)
		.first()
	)
	if ccp and ccp.custom_price:
		return ccp.custom_price

	# ② 店舗ランク標準
	rank_course = (
		RankCourse.objects
		.filter(store=rc.reservation.store,
				rank=rc.cast_profile.rank,
				course=rc.course)
		.first()
	)
	return rank_course.base_price if rank_course else 0



def _latest_cast_rate_map(target: date) -> dict[int, tuple[int|None, Decimal]]:
	"""
	cast_profile_id ➜ (hourly_rate, commission_pct)
	RDB に依存しない方法で「最新レートだけ」を抜き出す
	"""
	rate_map: dict[int, tuple[int|None, Decimal]] = {}
	qs = (
		CastRate.objects
		.filter(effective_from__lte=target)
		.order_by('cast_profile', '-effective_from')   # 新しい順に並ぶ
	)
	for r in qs:
		# 1回目に出てきたレコード = cast_profile ごとの最新
		rate_map.setdefault(
			r.cast_profile_id,
			(r.hourly_rate, r.commission_pct or Decimal('0'))
		)
	return rate_map

# --- 追加: driver 用ヘルパ --------------------------
def _latest_driver_rate_map(target: date) -> dict[int, int]:
	"""
	driver_id ➜ hourly_rate
	DISTINCT ON を使わずに Python 側で「最新レコードだけ」を抽出
	"""
	drv_map: Dict[int, int] = {}
	qs = (
		DriverRate.objects
		.filter(effective_from__lte=target)
		.order_by('driver', '-effective_from')   # 新しい順
	)
	for r in qs:
		drv_map.setdefault(r.driver_id, r.hourly_rate or 0)
	return drv_map

def _calc_cast_labor(target: date, store=None) -> int:
	"""
	時給制キャスト → (勤務時間 × 時給)
	歩合キャスト   → (コース素価格 × commission_pct) + (オプション合計 × 50%)
	"""

	# ── 最新レート辞書（cast_id ➜ (hourly, pct)）──
	latest_rates = (
		CastRate.objects
		.filter(effective_from__lte=target)
		.order_by('cast_profile', '-effective_from')
		.distinct('cast_profile')
	)
	rate_map = _latest_cast_rate_map(target)
	total = 0

	# ───────────────────────────────────
	# ① 時給キャスト（打刻から算出）
	# ───────────────────────────────────
	sa_qs = ShiftAttendance.objects.filter(
		checked_in_at__date=target,
		checked_out_at__isnull=False,
	)
	if store:
		sa_qs = sa_qs.filter(cast_profile__store_id=store)

	for sa in sa_qs.select_related('cast_profile'):
		hr, pct = rate_map.get(sa.cast_profile_id, (None, None))
		if hr:   # 時給があればそれを採用
			hours = (sa.checked_out_at - sa.checked_in_at).total_seconds() / 3600
			total += hr * hours

	# ───────────────────────────────────
	# ② 歩合キャスト（予約から算出）
	# ───────────────────────────────────
	res_qs = Reservation.objects.filter(start_at__date=target)
	if store:
		res_qs = res_qs.filter(store_id=store)


	# 予約→オプション売上合計（OPTION のみ）
	opt_sum = (
		ReservationCharge.objects
		.filter(reservation__in=res_qs, kind='OPTION')
		.values('reservation')
		.annotate(s=Sum('amount'))   # ← ここを 'amount' に
	)
	opt_map = {row['reservation']: row['s'] or 0 for row in opt_sum}

	# 歩合キャストごとに人件費を積算
	rc_qs = (
		ReservationCast.objects
		.filter(reservation__in=res_qs)
		.select_related('reservation', 'cast_profile', 'course')
	)
	for rc in rc_qs:
		hr, pct = rate_map.get(rc.cast_profile_id, (None, None))
		if hr:		# 時給設定がある人は①ですでに計上済み
			continue
		if not pct:   # どちらも入っていなければ 0
			continue

		base_price  = _base_course_price(rc)
		option_part = Decimal(opt_map.get(rc.reservation_id, 0)) * Decimal('0.5')
		total += (Decimal(base_price) * (pct / Decimal('100'))) + option_part

	return int(total)


def get_daily_pl(target_date: dt, store_id: int | None = None) -> dict:

    # ---------- フィルタ ----------
    rsv_qs = Reservation.objects.filter(start_at__date=target_date)
    if store_id:
        rsv_qs = rsv_qs.filter(store_id=store_id)

    # ---------- 売上内訳 ----------
    pay_qs = Payment.objects.filter(reservation__in=rsv_qs)

    sales_cash = pay_qs.filter(method=Payment.CASH) \
                       .aggregate(t=Coalesce(Sum('amount'), 0))['t']
    sales_card = pay_qs.filter(method=Payment.CARD) \
                       .aggregate(t=Coalesce(Sum('amount'), 0))['t']
    sales_total = sales_cash + sales_card

    # ---------- キャスト人件費 ----------
    # 例：時給 × 稼働時間 で計算（ざっくりサンプル）
    cast_labor = rsv_qs.aggregate(
        t=Coalesce(Sum('casts__course__minutes'), 0)  # ←雑に時間を足してるだけ
    )['t'] // 60 * 2000                              # 時給 2000 円想定

    # ---------- ドライバー人件費 ----------
    driver_labor = rsv_qs.count() * 1000  # ← 1 件あたり 1000 円の仮定

    # ---------- 手入力経費 ----------
    custom_expense = ManualEntry.objects.filter(
        reservation__in=rsv_qs,
        entry_type=ManualEntry.EXPENSE
    ).aggregate(t=Coalesce(Sum('amount'), 0))['t']

    # ---------- 粗利 ----------
    gross_profit = sales_total - cast_labor - driver_labor - custom_expense

    return {
        "date": target_date,
        "store_id": store_id,
        "sales_cash": sales_cash,
        "sales_card": sales_card,
        "sales_total": sales_total,
        "cast_labor": cast_labor,
        "driver_labor": driver_labor,
        "custom_expense": custom_expense,
        "gross_profit": gross_profit,
    }




def get_monthly_pl(year: int, month: int, store: int | None = None) -> dict:
	"""1 か月分の日次 + 月次サマリを返す"""
	first_day = date(year, month, 1)
	days_in_month = monthrange(year, month)[1]

	daily_rows: list[dict] = []
	totals = {
		"sales_cash": 0, "sales_card": 0, "sales_total": 0,
		"cast_labor": 0, "driver_labor": 0,
		"custom_expense": 0, "gross_profit": 0,
	}

	# 日次を回しながら集計
	for d in range(days_in_month):
		curr = first_day + timedelta(days=d)
		row  = get_daily_pl(curr, store)
		daily_rows.append(row)
		for k in totals:
			totals[k] += row[k] 

	# 固定費・カスタム経費（月合計）はここで計算
	last_day = first_day.replace(day=days_in_month)
	fx_qs = ExpenseEntry.objects.filter(
		date__range=(first_day, last_day), category__is_fixed=True
	)
	ct_qs = ExpenseEntry.objects.filter(
		date__range=(first_day, last_day), category__is_fixed=False
	)
	if store:
		fx_qs = fx_qs.filter(store_id__in=[store, None])
		ct_qs = ct_qs.filter(store_id=store)

	fixed_exp   = fx_qs.aggregate(s=Sum("amount"))["s"] or 0
	custom_exp  = ct_qs.aggregate(s=Sum("amount"))["s"] or 0	  # 重複しないよう上書き
	operating   = totals["sales_total"] - totals["cast_labor"] - totals["driver_labor"] \
				  - fixed_exp - custom_exp

	# ① ラベル別固定費を GROUP BY
	fx_breakdown = (
		fx_qs
		.values('category__name')
		.annotate(amount=Sum('amount'))
		.order_by('category__name')
	)
	fixed_breakdown = [
		{"name": row['category__name'], "amount": row['amount'] or 0}
		for row in fx_breakdown
	]

	month_key = f"{year}-{month:02d}"

	return {
		"month": month_key,
		"days":  daily_rows,
		"monthly_total": totals,
		# 以下は Yearly 用のサマリ
		"sales_total": totals["sales_total"],
		"sales_cash":   totals["sales_cash"],
		"sales_card":   totals["sales_card"],
		"cast_labor":  totals["cast_labor"],
		"driver_labor": totals["driver_labor"],
		"fixed_expense": fixed_exp,
		"fixed_breakdown": fixed_breakdown, 
		"custom_expense": custom_exp,
		"operating_profit": operating,

	}

def get_yearly_pl(year: int, store: int | None = None) -> list[dict]:
	"""12 か月サマリをリストで返す"""
	return [get_monthly_pl(year, m, store) for m in range(1, 13)]