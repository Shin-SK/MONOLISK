from __future__ import annotations
"""
pl_yearly.py (Step‑7): 月次 PL を 12 ヶ月合算して年間 PL
"""
from datetime import date
from typing import Dict, Any

from billing.utils.pl_monthly import get_monthly_pl

__all__ = ["get_yearly_pl"]


def get_yearly_pl(year: int, *, store_id: int) -> Dict[str, Any]:
    months: list[Dict[str, Any]] = []
    totals = {
        "sales_total": 0, "guest_count": 0,
        "labor_cost": 0,  "operating_profit": 0,
    }

    for m in range(1, 13):
        mpl = get_monthly_pl(year, m, store_id=store_id)
        months.append({"month": m, "totals": mpl})
        for k in totals:
            totals[k] += mpl[k]

    totals["avg_spend"] = int(
        totals["sales_total"] // totals["guest_count"]
    ) if totals["guest_count"] else 0

    return {
        "year": year,
        "store_id": store_id,
        "months": months,      # ★ 追加
        "totals": totals,
    }