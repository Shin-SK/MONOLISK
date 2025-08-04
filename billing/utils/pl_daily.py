from __future__ import annotations
"""
Step‑3: 日次 P/L 計算ユーティリティを BillCalculator に統一
 - open Bill (未 close) の金額も BillCalculator で算出
 - 旧 _calc_open_bill_total() はラッパとして存続
"""

from collections import defaultdict
from datetime    import date
from typing      import Any, Dict

from django.db.models import F, Sum
from django.db.models.functions import Coalesce

from billing.models  import Bill, BillItem
from billing.utils.services import cast_payout_sum, cast_payroll_sum
from billing.calculator import BillCalculator

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

def get_daily_pl(
    target_date: date,
    *,
    store_id: int,
    include_breakdown: bool = False,
) -> Dict[str, Any]:
    """指定日・指定店舗の P/L＋KPI 一覧"""
    if store_id is None:
        raise ValueError("store_id は必須です（店舗単位集計のみ想定）")

    # ── 1) 対象 Bill ────────────────────────────
    bills = (
        Bill.objects
        .filter(opened_at__date=target_date, table__store_id=store_id)
        .select_related("table__store")
        .prefetch_related("items")
    )

    subtotal_sum = 0
    sales_total  = 0
    for b in bills:
        # subtotal は Bill.subtotal があればそのまま、無ければ item 集計
        if b.subtotal:
            subtotal_sum += b.subtotal
        else:
            subtotal_sum += b.items.aggregate(
                s=Coalesce(Sum(F("price") * F("qty")), 0)
            )["s"]

        # total は close 済なら Bill.total、未 close なら Calculator
        sales_total += b.total or _calc_open_bill_total(b)

    # ── 2) 明細アイテム ─────────────────────────
    items = (
        BillItem.objects
        .filter(bill__in=bills)
        .select_related("item_master__category")
    )

    # 来客数（SET 系 qty 合計）
    guest_items = items.filter(item_master__category__code__iregex=r"^(set|seat)")
    guest_count = guest_items.aggregate(c=Coalesce(Sum("qty"), 0))["c"]

    # VIP 比率（SET 商品コード末尾 _vip）
    vip_set_qty = guest_items.filter(item_master__code__endswith="_vip").aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    vip_ratio = vip_set_qty / guest_count if guest_count else 0

    # 延長回数
    extension_qty = items.filter(item_master__category__code="ext").aggregate(c=Coalesce(Sum("qty"), 0))["c"]

    # ドリンク売上・杯数・単価
    drink_items = items.filter(item_master__category__code="drink")
    drink_sales = drink_items.aggregate(s=Coalesce(Sum(F("price") * F("qty")), 0))["s"]
    drink_qty   = drink_items.aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    drink_unit_price = int(drink_sales // drink_qty) if drink_qty else 0

    # 平均客単価
    avg_spend = int(sales_total // guest_count) if guest_count else 0

    # 3) breakdown (optional)
    category_breakdown: Dict[str, int] | None = None
    if include_breakdown:
        category_breakdown = defaultdict(int)
        rows = (
            items.values(code=F("item_master__category__code")).annotate(total=Sum(F("price") * F("qty")))
        )
        for r in rows:
            category_breakdown[r["code"]] += r["total"]
        category_breakdown = dict(category_breakdown)

    # 4) 人件費 & 営業利益
    labor_cost = cast_payroll_sum(target_date, target_date, store_id)
    operating_profit = int(sales_total - labor_cost)

    # 結果組み立て
    result: Dict[str, Any] = {
        "date"            : target_date.isoformat(),
        "store_id"        : store_id,
        "guest_count"     : guest_count,
        "subtotal"        : int(subtotal_sum),
        "sales_total"     : int(sales_total),
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
        result["category_breakdown"] = category_breakdown

    return result
