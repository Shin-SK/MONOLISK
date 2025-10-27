# billing/utils/pl_monthly.py
from __future__ import annotations
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
    first = date(year, month, 1)
    last  = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    agg = {
        "sales_cash": 0, "sales_card": 0, "sales_total": 0,
        "guest_count": 0,
        "commission": 0, "hourly_pay": 0, "labor_cost": 0,
        "operating_profit": 0,
    }

    for d in _daterange_day(first, last):
        day = get_daily_pl(d, store_id=store_id)
        cash = int(day.get("sales_cash") or 0)
        card = int(day.get("sales_card") or 0)
        day_total = int(day.get("sales_total") or (cash + card))

        agg["sales_cash"]        += cash
        agg["sales_card"]        += card
        agg["sales_total"]       += day_total
        agg["guest_count"]       += int(day.get("guest_count") or 0)
        agg["commission"]        += int(day.get("commission") or 0)
        agg["hourly_pay"]        += int(day.get("hourly_pay") or 0)
        agg["labor_cost"]        += int(day.get("labor_cost") or 0)
        agg["operating_profit"]  += int(day.get("operating_profit") or 0)

    avg_spend = int(agg["sales_total"] // agg["guest_count"]) if agg["guest_count"] else 0

    return {
        "year": year, "month": month, "store_id": store_id,
        **agg, "avg_spend": avg_spend,
    }
