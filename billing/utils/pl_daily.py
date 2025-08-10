# utils/pl_daily.py
from __future__ import annotations

from collections import defaultdict
from datetime    import date
from typing      import Any, Dict

from django.db.models import F, Sum
from django.db.models.functions import Coalesce

from billing.models  import Bill, BillItem
from billing.utils.services import cast_payout_sum_by_closed_window, cast_payroll_sum_by_business_date
from billing.calculator import BillCalculator
from billing.utils.bizday import get_business_window


__all__ = ["get_daily_pl"]

# ------------------------------------------------------------------
# helper
# ------------------------------------------------------------------

def _calc_open_bill_total(bill: Bill) -> int:
    """Bill.total==0（未 close）の場合でも BillCalculator で再計算して返す"""
    return BillCalculator(bill).execute().total

# ------------------------------------------------------------------
# public API
# ------------------------------------------------------------------

def get_daily_pl(target_date: date, *, store_id: int, include_breakdown: bool = False):
    # 1) 営業日ウィンドウ（[start, end)）
    start_dt, end_dt = get_business_window(target_date, store_id=store_id)

    # 2) 対象 Bill：営業日ウィンドウで close 済み
    bills = (
        Bill.objects
        .filter(closed_at__gte=start_dt, closed_at__lt=end_dt, table__store_id=store_id)
        .select_related("table__store")
        .prefetch_related("items")
    )

    # 3) subtotal はウィンドウ内伝票の明細合計
    subtotal_sum = (
        BillItem.objects
        .filter(bill__in=bills)
        .aggregate(s=Coalesce(Sum(F("price") * F("qty")), 0))
    )["s"] or 0

    # 4) 売上（計）：基本は Bill.total 合算。未セット補完は BillCalculator
    total_agg = bills.aggregate(s=Coalesce(Sum("total"), 0))["s"] or 0
    if any(b.total in (None, 0) for b in bills):
        sales_total = sum(b.total or BillCalculator(b).execute().total for b in bills)
    else:
        sales_total = total_agg

    # 5) 明細から各 KPI
    items = BillItem.objects.filter(bill__in=bills).select_related("item_master__category")

    guest_items = items.filter(item_master__category__code__iregex=r"^(set|seat)")
    guest_count = guest_items.aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    vip_set_qty = guest_items.filter(item_master__code__endswith="_vip").aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    vip_ratio   = vip_set_qty / guest_count if guest_count else 0
    extension_qty = items.filter(item_master__category__code="ext").aggregate(c=Coalesce(Sum("qty"), 0))["c"]

    drink_items = items.filter(item_master__category__code="drink")
    drink_sales = drink_items.aggregate(s=Coalesce(Sum(F("price") * F("qty")), 0))["s"]
    drink_qty   = drink_items.aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    drink_unit_price = int(drink_sales // drink_qty) if drink_qty else 0

    avg_spend = int(sales_total // guest_count) if guest_count else 0

    # 6) 現金/カード（ウィンドウ内）
    paid_sums = bills.aggregate(
        sales_cash=Coalesce(Sum("paid_cash"), 0),
        sales_card=Coalesce(Sum("paid_card"), 0),
    )
    sales_cash = int(paid_sums["sales_cash"] or 0)
    sales_card = int(paid_sums["sales_card"] or 0)

    # 7) 人件費：歩合=closed_atベースのまま / 時給=営業日(business_date)ベース
    payroll_cost    = cast_payroll_sum_by_business_date(target_date, target_date, store_id)
    commission_cost = cast_payout_sum_by_closed_window(start_dt, end_dt, store_id)
    labor_cost = int(payroll_cost) + int(commission_cost)

    operating_profit = int(sales_total - labor_cost)

    result = {
        "date"            : target_date.isoformat(),
        "store_id"        : store_id,
        "guest_count"     : guest_count,
        "subtotal"        : int(subtotal_sum),
        "sales_total"     : int(sales_total),
        "sales_cash"      : sales_cash,
        "sales_card"      : sales_card,
        "avg_spend"       : avg_spend,
        "drink_sales"     : int(drink_sales),
        "drink_qty"       : drink_qty,
        "drink_unit_price": drink_unit_price,
        "extension_qty"   : extension_qty,
        "vip_ratio"       : vip_ratio,
        "labor_cost"      : int(labor_cost),
        "operating_profit": operating_profit,
    }
    if include_breakdown:
        # 省略（既存のまま）
        pass
    return result
