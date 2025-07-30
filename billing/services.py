# billing/services.py
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Case, When, IntegerField, F, Q, Value
from django.db.models.functions import Coalesce
from .models import Cast, CastPayout

def calc_bill_totals(bill):
	items	 = bill.items.select_related('item_master', 'served_by_cast')
	subtotal = sum(i.subtotal for i in items)

	store	 = bill.table.store
	svc_rate = Decimal(store.service_rate)
	tax_rate = Decimal(store.tax_rate)

	service_amt = round(sum(i.subtotal
							for i in items
							if i.item_master.apply_service) * svc_rate)
	tax_amt		= round((subtotal + service_amt) * tax_rate)

	# ─────────────────────────────────────
	# ❶ 本指名キャスト集合（stay 行が無くても拾う）
	nom_ids = set()
	if bill.main_cast_id:
		nom_ids.add(bill.main_cast_id)
	nom_ids.update(bill.nominated_casts.values_list('id', flat=True))
	nom_ids.update(
		bill.stays.filter(stay_type='nom')
				  .values_list('cast_id', flat=True)
	)
	nom_cast_map = {c.id: c for c in Cast.objects.filter(id__in=nom_ids)}

	# ─────────────────────────────────────
	# ❷ 個別バック ＆ プール振り分け
	payout_rows = []		# [(cast, bill_item, amt), …]
	for it in items:
		if it.exclude_from_payout or it.back_rate == 0:
			continue

		amt = round(it.subtotal * it.back_rate)

		if it.served_by_cast_id in nom_ids:
			# 本指名キャスト絡みの品目 → プールへ
			payout_rows.append(('NOM_POOL', it, amt))
		else:
			# フリー／場内 → 個別バック
			payout_rows.append((it.served_by_cast, it, amt))

	# ─────────────────────────────────────
	# ❸ プール再配分
	pool_rate  = store.nom_pool_rate
	pool_total = int((Decimal(subtotal) * pool_rate)
					 .quantize(Decimal('1'), ROUND_HALF_UP))

	weight_map = {
		s.cast_id: (s.nom_weight or Decimal('1'))
		for s in bill.stays.filter(stay_type='nom')
	}
	weights	 = [weight_map.get(cid, Decimal('1')) for cid in nom_ids]
	weight_sum = sum(weights) or Decimal('1')

	pool_rows, rest = [], pool_total
	for cid, w in zip(nom_ids, weights):
		share = int((pool_total * w / weight_sum)
					.quantize(Decimal('1'), ROUND_HALF_UP))
		rest -= share
		pool_rows.append((nom_cast_map[cid], None, share))

	if rest and pool_rows:				# 1 円余り補正
		c, bi, amt = pool_rows[0]
		pool_rows[0] = (c, bi, amt + rest)

	# ─────────────────────────────────────
	fixed_item_rows = [
		(c, bi, amt) for (c, bi, amt) in payout_rows
		if c != 'NOM_POOL'
	]
	payouts = fixed_item_rows + pool_rows

	return {
		'subtotal': subtotal,
		'service' : service_amt,
		'tax'	 : tax_amt,
		'total'   : subtotal + service_amt + tax_amt,
		'payouts' : payouts,
	}







def get_cast_sales(date_from, date_to, store_id=None):
    """
    指定期間 & 店舗で “全キャスト” の売上サマリを返す。
      ‑ 集計０件のキャストも 0 埋めで必ず出す
    """
    # ─ 集計対象 Cast 一覧 ─────────────────────────
    cast_qs = Cast.objects.all()
    if store_id:
        cast_qs = cast_qs.filter(store_id=store_id)

    # ─ 期間内の CastPayout をベースに各種集計 ──────
    period_payouts = CastPayout.objects.filter(
        bill__opened_at__date__range=(date_from, date_to)
    )

    cast_qs = (
        cast_qs
        .annotate(
            sales_nom=Coalesce(Sum(
                Case(
                    When(
                        payouts__in=period_payouts,
                        payouts__bill__stays__stay_type='nom',
                        payouts__bill__stays__cast_id=F('id'),
                        then='payouts__amount'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ), 0),
            sales_in=Coalesce(Sum(
                Case(
                    When(
                        payouts__in=period_payouts,
                        payouts__bill__stays__stay_type='in',
                        payouts__bill__stays__cast_id=F('id'),
                        then='payouts__amount'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ), 0),
            sales_free=Coalesce(Sum(
                Case(
                    When(
                        payouts__in=period_payouts,
                        payouts__bill__stays__stay_type='free',
                        payouts__bill__stays__cast_id=F('id'),
                        then='payouts__amount'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ), 0),
        )
        .annotate(total=F('sales_nom') + F('sales_in') + F('sales_free'))
        .order_by('-total')
    )

    return list(
        cast_qs.values(
            'stage_name',                  # ← フィールドそのまま列挙
            cast_id       = F('id'),
            sales_nom     = F('sales_nom'),
            sales_in      = F('sales_in'),
            sales_free    = F('sales_free'),
            sales_champ   = Value(0, output_field=IntegerField()),
            total         = F('total'),
        )
    )



# billing/services.py
from typing import Iterable, Set
from .models import Bill, BillItem, ItemMaster

_MAIN_FEE_CODE   = "mainNom-fee"      # ← ItemMaster.code
_INHOUSE_FEE_CODE = "houseNom-fee"    # ← ItemMaster.code


def _sync_fee_lines(
    bill: Bill,
    cast_ids_added: Iterable[int],
    cast_ids_removed: Iterable[int],
    item_code: str,
):
    """差分だけ BillItem を追加／削除する共通ルーチン"""
    master = ItemMaster.objects.get(code=item_code)

    # 追加 ────────────────────────────
    for cid in cast_ids_added:
        BillItem.objects.get_or_create(
            bill=bill,
            item_master=master,
            served_by_cast_id=cid,
            defaults=dict(
                qty=1,
                price=master.price_regular,     # 販売価格
                exclude_from_payout=True,       # 歩合の対象外なら (任意)
            ),
        )

    # 削除 ────────────────────────────
    if cast_ids_removed:
        BillItem.objects.filter(
            bill=bill,
            item_master=master,
            served_by_cast_id__in=cast_ids_removed,
        ).delete()


def sync_nomination_fees(
    bill: Bill,
    prev_main: Set[int], new_main: Set[int],
    prev_in:   Set[int], new_in:   Set[int],
):
    """
    ・mainNom‑fee / houseNom‑fee の BillItem を差分で整合させる
    ・最後に bill.recalc() で金額を確定
    """
    _sync_fee_lines(
        bill,
        cast_ids_added=new_main - prev_main,
        cast_ids_removed=prev_main - new_main,
        item_code=_MAIN_FEE_CODE,
    )
    _sync_fee_lines(
        bill,
        cast_ids_added=new_in - prev_in,
        cast_ids_removed=prev_in - new_in,
        item_code=_INHOUSE_FEE_CODE,
    )

    # 金額の再計算は 1 回で OK
    bill.recalc(save=True)
