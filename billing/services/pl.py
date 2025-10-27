# billing/services/pl.py  ← 新規ファイル
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, F, Q, Value, IntegerField, Count
from django.db.models.functions import Coalesce
from billing.models import Bill, CastPayout, CastDailySummary

def _bill_qs(store_id, df, dt):
    return (Bill.objects
            .filter(table__store_id=store_id, closed_at__isnull=False,
                    closed_at__date__range=(df, dt)))

def _coalesced_total():
    # settled_total 優先、なければ grand_total
    return Coalesce('settled_total', 'grand_total', Value(0), output_field=IntegerField())

def pl_range(store_id: int, df, dt):
    bills = _bill_qs(store_id, df, dt)

    agg = bills.aggregate(
        sales_total = Sum(_coalesced_total()),
        sales_cash  = Sum('paid_cash'),
        sales_card  = Sum('paid_card'),
        guest_count = Count('id'),
    )
    sales_total = int(agg['sales_total'] or 0)
    sales_cash  = int(agg['sales_cash']  or 0)
    sales_card  = int(agg['sales_card']  or 0)
    guest_count = int(agg['guest_count'] or 0)

    # 歩合（出来高）＝ CastPayout
    commission = int(CastPayout.objects
                     .filter(bill__in=bills)
                     .aggregate(x=Sum('amount'))['x'] or 0)

    # 時給（固定）＝ CastDailySummary.payroll
    hourly_pay = int(CastDailySummary.objects
                     .filter(store_id=store_id,
                             work_date__range=(df, dt))
                     .aggregate(x=Sum('payroll'))['x'] or 0)

    labor_cost = commission + hourly_pay

    return {
        'sales_total': sales_total,
        'sales_cash': sales_cash,
        'sales_card': sales_card,
        'guest_count': guest_count,
        'avg_spend': int(sales_total // guest_count) if guest_count else 0,
        'commission': commission,         # 出来高（CastPayout 合計）
        'hourly_pay': hourly_pay,         # 時給合計（CastDailySummary）
        'labor_cost': labor_cost,         # 人件費トータル
        'operating_profit': sales_total - labor_cost,   # 必要なら他コストを後で差し引き
    }

def pl_daily(store_id: int, d):
    return pl_range(store_id, d, d)

def pl_monthly(store_id: int, year: int, month: int):
    from calendar import monthrange
    last = monthrange(year, month)[1]
    df, dt = date(year, month, 1), date(year, month, last)
    days = []
    cur = df
    while cur <= dt:
        days.append({'date': cur.isoformat(), **pl_daily(store_id, cur)})
        cur += timedelta(days=1)
    monthly_total = pl_range(store_id, df, dt)
    return {'year': year, 'month': month, 'days': days, 'monthly_total': monthly_total}

def pl_yearly(store_id: int, year: int):
    months = []
    for m in range(1, 13):
        from calendar import monthrange
        last = monthrange(year, m)[1]
        df, dt = date(year, m, 1), date(year, m, last)
        months.append({'month': m, 'totals': pl_range(store_id, df, dt)})
    totals_year = pl_range(store_id, date(year,1,1), date(year,12,31))
    return {'year': year, 'months': months, 'totals': totals_year}
