from datetime    import date, timedelta
from calendar    import monthrange
from typing      import Dict, List

from billing.utils.pl_daily import get_daily_pl


def get_monthly_pl(year: int, month: int,
                   store_id: int | None = None) -> Dict:
	"""
	month 単位の P/L 集計 + 日次明細を返す。
	"""
	first_day     = date(year, month, 1)
	days_in_month = monthrange(year, month)[1]

	days: List[Dict] = []
	totals = {
		"guest_count"     : 0,
		"sales_total"     : 0,
		"drink_sales"     : 0,
		"drink_qty"       : 0,
		"extension_qty"   : 0,
		"labor_cost"      : 0,
		"operating_profit": 0,
	}

	for d in range(days_in_month):
		curr = first_day + timedelta(days=d)
		row  = get_daily_pl(curr, store_id)
		days.append(row)

		for k in totals:
			totals[k] += row[k]

	# 平均系・率系を再計算
	totals["avg_spend"]        = (
		totals["sales_total"] // totals["guest_count"]
		if totals["guest_count"] else 0
	)
	totals["drink_unit_price"] = (
		totals["drink_sales"] // totals["drink_qty"]
		if totals["drink_qty"] else 0
	)
	totals["vip_ratio"] = 0   # （必要なら取得）

	return {
		"year"    : year,
		"month"   : month,
		"store_id": store_id,
		"days"    : days,
		"totals"  : totals,
	}
