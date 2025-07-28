from django.db.models import Sum

from billing.models import CastPayout


def cast_payout_sum(date_from, date_to, store_id=None):
	"""
	指定日付範囲の CastPayout.amount 合計を返す。
	store_id が空文字列や None のときは全店。
	"""
	# ① まず必ず qs を作る
	qs = CastPayout.objects.filter(
		bill__closed_at__date__range=(date_from, date_to)
	)

	# ② 店舗絞り込み（store_id が Truthy のときだけ）
	if store_id:
		qs = qs.filter(bill__table__store_id=store_id)

	# ③ 合計を返す。該当無しなら 0
	return qs.aggregate(total=Sum('amount'))['total'] or 0