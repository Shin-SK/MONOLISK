# billing/utils/pl_yearly.py
from typing import List, Dict
from billing.utils.pl_monthly import get_monthly_pl


def get_yearly_pl(year: int, store_id: int | None = None) -> Dict:
    """
    12 か月分の月次 P/L と年間サマリ
    """
    months: List[Dict] = [get_monthly_pl(year, m, store_id) for m in range(1, 13)]

    totals = {
        "guest_count":   sum(m["totals"]["guest_count"]   for m in months),
        "sales_total":   sum(m["totals"]["sales_total"]   for m in months),
        "drink_sales":   sum(m["totals"]["drink_sales"]   for m in months),
        "drink_qty":     sum(m["totals"]["drink_qty"]     for m in months),
        "extension_qty": sum(m["totals"]["extension_qty"] for m in months),
    }
    totals["avg_spend"]        = totals["sales_total"] / totals["guest_count"] \
                                 if totals["guest_count"] else 0
    totals["drink_unit_price"] = totals["drink_sales"] / totals["drink_qty"] \
                                 if totals["drink_qty"] else 0
    totals["vip_ratio"] = 0     # 要件次第でどうぞ

    return {
        "year": year,
        "store_id": store_id,
        "months": months,
        "totals": totals,
    }
