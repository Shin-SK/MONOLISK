# billing/utils/pl_monthly.py
from __future__ import annotations
"""
pl_monthly.py: 日次 PL を合算して月次 PL を返す（closed_at ベースの現金/カード対応）
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
    """指定年月・店舗の月次 PL（各日の daily を単純合算）"""
    first = date(year, month, 1)
    # 月末（翌月1日の前日）
    last  = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    agg = {
        "sales_cash": 0,
        "sales_card": 0,
        "sales_total": 0,      # ← 月次売上は cash+card の合計でそろえる
        "guest_count": 0,
        "labor_cost": 0,
        "operating_profit": 0, # = 日次 operating_profit の合計
    }

    for d in _daterange_day(first, last):
        day = get_daily_pl(d, store_id=store_id)
        cash = int(day.get("sales_cash") or 0)
        card = int(day.get("sales_card") or 0)
        # daily の sales_total が未設定でも cash+card で整合させる
        day_total = int(day.get("sales_total") or (cash + card))

        agg["sales_cash"]        += cash
        agg["sales_card"]        += card
        agg["sales_total"]       += day_total
        agg["guest_count"]       += int(day.get("guest_count") or 0)
        agg["labor_cost"]        += int(day.get("labor_cost") or 0)
        agg["operating_profit"]  += int(day.get("operating_profit") or 0)

    avg_spend = int(agg["sales_total"] // agg["guest_count"]) if agg["guest_count"] else 0

    return {
        "year": year,
        "month": month,
        "store_id": store_id,
        **agg,
        "avg_spend": avg_spend,
    }
