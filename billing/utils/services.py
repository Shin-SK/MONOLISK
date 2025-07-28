# billing/utils/services.py
from django.db.models import Sum
from billing.models import CastPayout     # 既にあれば重複 import は削って OK


def cast_payout_sum(date_from, date_to, store_id=None):
	"""
	指定日付範囲の CastPayout.amount 合計値を返す。
	- store_id が None/空文字/0 等なら全店合算
	- 結果が 0 件なら 0 を返す（None を回避）
	"""
	# ① 必ず qs を先に作る
	qs = CastPayout.objects.filter(
		bill__closed_at__date__range=(date_from, date_to)
	)

	# ② 店舗スコープ（Truth‑y のときだけ）
	if store_id:
		qs = qs.filter(bill__table__store_id=store_id)

	# ③ 合計額を返す
	return qs.aggregate(total=Sum('amount'))['total'] or 0
