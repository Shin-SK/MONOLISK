# billing/utils/services.py
from django.db.models import Sum
from django.db.models.functions import Coalesce
from billing.models import CastPayout, CastDailySummary

def cast_payout_sum(date_from, date_to, store_id=None):
    """
    カレンダー日(date)で CastPayout.amount を合計。
    ※ 営業日ウィンドウではなく「日付ベース」で使いたいところ向け。
    """
    qs = CastPayout.objects.filter(
        bill__closed_at__date__range=(date_from, date_to)
    )
    if store_id:
        qs = qs.filter(bill__table__store_id=store_id)
    total = qs.aggregate(total=Coalesce(Sum('amount'), 0))['total'] or 0
    return int(total)

def cast_payroll_sum(date_from, date_to, store_id=None):
    """
    旧：勤務日(work_date)ベースの時給合計
    """
    qs = CastDailySummary.objects.filter(work_date__range=(date_from, date_to))
    if store_id:
        qs = qs.filter(store_id=store_id)
    total = qs.aggregate(total=Coalesce(Sum('payroll'), 0))['total'] or 0
    return int(total)

def cast_payroll_sum_by_business_date(from_date, to_date, store_id) -> int:
    """
    営業日(business_date)ベースの時給合計
    """
    qs = CastDailySummary.objects.filter(
        store_id=store_id,
        business_date__range=(from_date, to_date),
    )
    return int(qs.aggregate(s=Coalesce(Sum("payroll"), 0))["s"] or 0)

def cast_payout_sum_by_closed_window(start_dt, end_dt, store_id: int) -> int:
    """
    会計時刻(closed_at)を [start_dt, end_dt) の時間窓で歩合合計
    """
    total = (
        CastPayout.objects
        .filter(
            bill__table__store_id=store_id,
            bill__closed_at__gte=start_dt,
            bill__closed_at__lt=end_dt,
        )
        .aggregate(s=Coalesce(Sum("amount"), 0))["s"] or 0
    )
    return int(total)
