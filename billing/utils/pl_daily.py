# utils/pl_daily.py
from __future__ import annotations
from datetime import date
from django.db.models import F, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from billing.models  import Bill, BillItem
from billing.utils.services import cast_payout_sum_by_closed_window, cast_payroll_sum_by_business_date
from billing.calculator import BillCalculator
from billing.utils.bizday import get_business_window

__all__ = ["get_daily_pl"]

def _calc_open_bill_total(bill: Bill) -> int:
    return BillCalculator(bill).execute().total

def get_daily_pl(target_date: date, *, store_id: int, include_breakdown: bool = False):
    start_dt, end_dt = get_business_window(target_date, store_id=store_id)

    bills = (
        Bill.objects
        .filter(closed_at__gte=start_dt, closed_at__lt=end_dt, table__store_id=store_id)
        .select_related("table__store")
        .prefetch_related("items")
    )

    subtotal_sum = (
        BillItem.objects
        .filter(bill__in=bills)
        .aggregate(s=Coalesce(Sum(F("price") * F("qty")), 0))
    )["s"] or 0

    # ★ 会計上は settled_total 優先、無ければ grand_total
    sales_total = bills.aggregate(
        s=Coalesce(Sum(Coalesce(F("settled_total"), F("grand_total"), Value(0), output_field=IntegerField())), 0)
    )["s"] or 0

    items = BillItem.objects.filter(bill__in=bills).select_related("item_master__category")

    guest_items = items.filter(item_master__category__code__iregex=r"^(set|seat)")
    guest_count = guest_items.aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    vip_set_qty = guest_items.filter(item_master__code__endswith="_vip").aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    vip_ratio   = (vip_set_qty / guest_count) if guest_count else 0

    extension_qty = items.filter(item_master__category__code="ext").aggregate(c=Coalesce(Sum("qty"), 0))["c"]

    drink_items = items.filter(item_master__category__code="drink")
    drink_sales = drink_items.aggregate(s=Coalesce(Sum(F("price") * F("qty")), 0))["s"]
    drink_qty   = drink_items.aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    drink_unit_price = int(drink_sales // drink_qty) if drink_qty else 0

    avg_spend = int(sales_total // guest_count) if guest_count else 0

    paid_sums = bills.aggregate(
        sales_cash=Coalesce(Sum("paid_cash"), 0),
        sales_card=Coalesce(Sum("paid_card"), 0),
    )
    sales_cash = int(paid_sums["sales_cash"] or 0)
    sales_card = int(paid_sums["sales_card"] or 0)

    # 人件費：歩合=CastPayout（closed window）/ 時給=CastDailySummary（business date）
    hourly_pay      = int(cast_payroll_sum_by_business_date(target_date, target_date, store_id) or 0)
    commission      = int(cast_payout_sum_by_closed_window(start_dt, end_dt, store_id) or 0)
    labor_cost      = int(hourly_pay + commission)
    operating_profit = int(sales_total - labor_cost)

    result = {
        "date"            : target_date.isoformat(),
        "store_id"        : store_id,
        "guest_count"     : int(guest_count or 0),
        "subtotal"        : int(subtotal_sum),
        "sales_total"     : int(sales_total),
        "sales_cash"      : sales_cash,
        "sales_card"      : sales_card,
        "avg_spend"       : avg_spend,
        "drink_sales"     : int(drink_sales or 0),
        "drink_qty"       : int(drink_qty or 0),
        "drink_unit_price": drink_unit_price,
        "extension_qty"   : int(extension_qty or 0),
        # ★ 内訳を明示
        "commission"      : commission,
        "hourly_pay"      : hourly_pay,
        "labor_cost"      : labor_cost,
        "operating_profit": operating_profit,
    }
    if include_breakdown:
        pass
    return result
