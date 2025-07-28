from django.db.models import Sum

from billing.models import CastPayout


def cast_payout_sum(date_from, date_to, store_id=None) -> int:
	"""
	指定期間 & 店舗のキャストバック総額を返す。
	    date_from / date_to : datetime.date または datetime
	    store_id            : None = 全店
	"""
	data = (qs.values('cast_id','cast__stage_name')
			.annotate(total=Sum('amount'))
			.order_by('-total'))
	qs = CastPayout.objects.filter(
		bill__opened_at__date__range=(date_from, date_to)
	)
	if store_id:
		qs = qs.filter(bill__table__store_id=store_id)

	return qs.aggregate(total=Sum("amount"))["total"] or 0
