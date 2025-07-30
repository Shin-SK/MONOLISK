from typing import Dict, List

from billing.utils.pl_monthly import get_monthly_pl


def get_yearly_pl(year: int, store_id: int | None = None) -> Dict:
	"""
	1 年分（12 か月）の月次 P/L + 年間サマリ
	"""
	months: List[Dict] = [
		get_monthly_pl(year, m, store_id=store_id) for m in range(1, 13)
	]

	totals = {
		"guest_count"     : sum(m["totals"]["guest_count"]     for m in months),
		"sales_total"     : sum(m["totals"]["sales_total"]     for m in months),
		"drink_sales"     : sum(m["totals"]["drink_sales"]     for m in months),
		"drink_qty"       : sum(m["totals"]["drink_qty"]       for m in months),
		"extension_qty"   : sum(m["totals"]["extension_qty"]   for m in months),
		"labor_cost"      : sum(m["totals"]["labor_cost"]      for m in months),
		"operating_profit": sum(m["totals"]["operating_profit"]for m in months),
	}
	totals["avg_spend"]        = (
		totals["sales_total"] // totals["guest_count"]
		if totals["guest_count"] else 0
	)
	totals["drink_unit_price"] = (
		totals["drink_sales"] // totals["drink_qty"]
		if totals["drink_qty"] else 0
	)
	totals["vip_ratio"] = 0

	return {
		"year"    : year,
		"store_id": store_id,
		"months"  : months,
		"totals"  : totals,
	}
