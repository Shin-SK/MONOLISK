# billing/utils/pl_monthly.py
from datetime import date, timedelta
from calendar import monthrange
from typing import Dict, List

from billing.utils.pl_daily import get_daily_pl        # さっき作ったやつ


def get_monthly_pl(year: int, month: int, store_id: int | None = None) -> Dict:
    """
    1 か月分の日次 P/L と月次サマリを返す
      year  : 2025
      month : 7
      store_id : 店舗 ID もしくは None
    """
    first_day       = date(year, month, 1)
    days_in_month   = monthrange(year, month)[1]
    daily_rows: List[Dict] = []

    # 合計用の箱
    totals = {
        "guest_count":     0,
        "sales_total":     0,
        "drink_sales":     0,
        "drink_qty":       0,
        "extension_qty":   0,
    }

    # 日次で回す
    for d in range(days_in_month):
        curr = first_day + timedelta(days=d)
        row  = get_daily_pl(curr, store_id)
        daily_rows.append(row)

        for k in totals:
            totals[k] += row[k]

    # 平均単価などは totals から再計算
    totals["avg_spend"]       = (
        totals["sales_total"]  / totals["guest_count"]
        if totals["guest_count"] else 0
    )
    totals["drink_unit_price"] = (
        totals["drink_sales"] / totals["drink_qty"]
        if totals["drink_qty"] else 0
    )
    totals["vip_ratio"] = 0       # （必要なら計算を追加）

    return {
        "year":   year,
        "month":  month,
        "store_id": store_id,
        "days":   daily_rows,
        "totals": totals,
    }
