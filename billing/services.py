# billing/services.py
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Case, When, IntegerField, F, Q
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
    指定期間（必須）と任意の store_id でキャスト別売上を返す。
    - date_from / date_to : 'YYYY‑MM‑DD' 文字列または date/datetime
    """
    qs = (
        CastPayout.objects
        .filter(bill__opened_at__date__range=(date_from, date_to))
        .values('cast_id', 'cast__stage_name')
        .annotate(
            sales_nom = Sum(
                Case(
                    When(
                        bill__stays__stay_type='nom',
                        bill__stays__cast_id=F('cast_id'),
                        then='amount'
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            sales_in = Sum(
                Case(
                    When(
                        bill__stays__stay_type='in',
                        bill__stays__cast_id=F('cast_id'),
                        then='amount'
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            sales_free = Sum(
                Case(
                    When(
                        bill__stays__stay_type='free',
                        bill__stays__cast_id=F('cast_id'),
                        then='amount'
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
        )
        .annotate(total=F('sales_nom') + F('sales_in') + F('sales_free'))
        .order_by('-total')
    )

    if store_id:
        qs = qs.filter(bill__table__store_id=store_id)

    return list(qs)      # ← dict リストで返す

