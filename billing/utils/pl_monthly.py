from __future__ import annotations
"""
pl_monthly.py (Step-7): 日次 PL を合算して月次 PL を返す
"""
from datetime import date, timedelta
from typing import Dict, Any

from billing.utils.pl_daily import get_daily_pl

__all__ = ["get_monthly_pl"]


def _daterange_day(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def get_monthly_pl(year: int, month: int, *, store_id: int) -> Dict[str, Any]:
    """指定年月・店舗の月次 PL を返す（daily PL の単純合算）"""
    first = date(year, month, 1)
    # 翌月1日を求めて1日引けば月末
    last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    agg = {
        "sales_total": 0,
        "guest_count": 0,
        "labor_cost": 0,
        "operating_profit": 0,
    }

    for d in _daterange_day(first, last):
        day_pl = get_daily_pl(d, store_id=store_id)
        for k in agg:
            agg[k] += day_pl[k]

    avg_spend = int(agg["sales_total"] // agg["guest_count"]) if agg["guest_count"] else 0

    return {
        "year": year,
        "month": month,
        "store_id": store_id,
        **agg,
        "avg_spend": avg_spend,
    }
