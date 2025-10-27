from __future__ import annotations
from typing import Dict, Any
from billing.utils.pl_monthly import get_monthly_pl

__all__ = ["get_yearly_pl"]

def get_yearly_pl(year: int, *, store_id: int) -> Dict[str, Any]:
    months: list[Dict[str, Any]] = []
    totals = {
        "sales_cash": 0, "sales_card": 0, "sales_total": 0,
        "guest_count": 0, "commission": 0, "hourly_pay": 0,
        "labor_cost": 0, "operating_profit": 0,
    }

    for m in range(1, 13):
        mpl = get_monthly_pl(year, m, store_id=store_id)
        months.append({"month": m, "totals": mpl})
        totals["sales_cash"]       += mpl.get("sales_cash", 0)
        totals["sales_card"]       += mpl.get("sales_card", 0)
        totals["sales_total"]      += mpl.get("sales_total", 0)
        totals["guest_count"]      += mpl.get("guest_count", 0)
        totals["commission"]       += mpl.get("commission", 0)
        totals["hourly_pay"]       += mpl.get("hourly_pay", 0)
        totals["labor_cost"]       += mpl.get("labor_cost", 0)
        totals["operating_profit"] += mpl.get("operating_profit", 0)

    totals["avg_spend"] = int(totals["sales_total"] // totals["guest_count"]) if totals["guest_count"] else 0
    return {"year": year, "store_id": store_id, "months": months, "totals": totals}
