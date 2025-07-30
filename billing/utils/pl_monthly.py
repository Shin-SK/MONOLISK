# billing/utils/pl_monthly.py  ―― まるごと貼り替え OK
from datetime    import date, timedelta
from calendar    import monthrange
from typing      import Dict, List

from billing.utils.pl_daily import get_daily_pl


def get_monthly_pl(year: int, month: int,
                   *,                     # ← store_id は keyword‑only
                   store_id: int) -> Dict:
    """
    指定年月 + 店舗の月次 P/L 集計。
      ‑ store_id は必須（全店集計は想定しない）
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
        # ★ get_daily_pl は store_id キーワード必須
        row  = get_daily_pl(curr, store_id=store_id)
        days.append(row)

        for k in totals:
            totals[k] += row[k]

    # 平均系・率系を再計算
    totals["avg_spend"] = (
        totals["sales_total"] // totals["guest_count"]
        if totals["guest_count"] else 0
    )
    totals["drink_unit_price"] = (
        totals["drink_sales"] // totals["drink_qty"]
        if totals["drink_qty"] else 0
    )
    totals["vip_ratio"] = 0   # 必要なら別途算出

    return {
        "year"    : year,
        "month"   : month,
        "store_id": store_id,
        "days"    : days,
        "totals"  : totals,
    }
