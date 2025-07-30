"""
日次 P/L & KPI 計算ユーティリティ
----------------------------------------------------------------
from datetime import date
from billing.utils.pl_daily import get_daily_pl

# 店舗 ID を必ず渡す！
get_daily_pl(date(2025, 7, 30), store_id=1)
"""
from __future__ import annotations

from collections import defaultdict
from datetime    import date
from decimal     import Decimal
from typing      import Any, Dict

from django.db.models import F, Sum
from django.db.models.functions import Coalesce

from billing.models         import Bill, BillItem
from billing.utils.services import cast_payout_sum
from billing.utils.services import cast_payroll_sum

__all__ = ["get_daily_pl"]


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _calc_open_bill_total(bill: Bill) -> int:
    """
    Bill.total==0（未 close）の場合でも
    サービス料・税を加味した金額を返す。
    """
    subtotal = bill.items.aggregate(
        s=Coalesce(Sum(F("price") * F("qty")), 0)
    )["s"]

    # テーブル未設定の仮伝票は税率 0 扱い
    store = bill.table.store if bill.table_id else None
    sr = Decimal(store.service_rate) if store else Decimal("0")
    tr = Decimal(store.tax_rate)    if store else Decimal("0")
    sr = sr / 100 if sr >= 1 else sr
    tr = tr / 100 if tr >= 1 else tr

    service = round(subtotal * sr)
    tax     = round((subtotal + service) * tr)
    return int(subtotal + service + tax)


# ------------------------------------------------------------------
# public API
# ------------------------------------------------------------------
def get_daily_pl(
    target_date: date,
    *,
    store_id: int,
    include_breakdown: bool = False,
) -> Dict[str, Any]:
    """
    指定日・指定店舗の P/L＋KPI を dict で返す。

    Parameters
    ----------
    target_date : datetime.date
    store_id    : int               ← **必須**
    include_breakdown : bool        True ならカテゴリ別売上も付ける
    """
    if store_id is None:
        raise ValueError("store_id は必須です（店舗単位集計のみ想定）")

    # ── 1) 該当 Bill ─────────────────────────────
    bills = (
        Bill.objects
        .filter(opened_at__date=target_date,
                table__store_id=store_id)
        .select_related("table__store")
        .prefetch_related("items")
    )

    subtotal_sum = 0
    sales_total  = 0
    for b in bills:
        subtotal_sum += b.subtotal or b.items.aggregate(
            s=Coalesce(Sum(F("price") * F("qty")), 0)
        )["s"]
        sales_total  += b.total or _calc_open_bill_total(b)

    # ── 2) 明細アイテム ───────────────────────────
    # KPI 全体は “show_in_menu” で絞らずに集計する
    items = (
        BillItem.objects
        .filter(bill__in=bills)
        .select_related("item_master__category")
    )

    # ―― 来客数（SET 系 qty 合計） ――――――――――――――――――――――――
    guest_items = items.filter(
        item_master__category__code__iregex=r'^(set|seat)'   # code が set*, seat* など
    )
    guest_count = guest_items.aggregate(
        c=Coalesce(Sum("qty"), 0)
    )["c"]

    # VIP 比率（SET 商品コード末尾 "_vip"）
    vip_set_qty = guest_items.filter(
        item_master__code__endswith="_vip"
    ).aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    vip_ratio = vip_set_qty / guest_count if guest_count else 0

    # ―― 延長回数 ―――――――――――――――――――――――――――――――――――――
    extension_qty = items.filter(
        item_master__category__code="ext"
    ).aggregate(c=Coalesce(Sum("qty"), 0))["c"]

    # ―― ドリンク売上・杯数・単価 ―――――――――――――――――――――
    drink_items = items.filter(
        item_master__category__code="drink"
    )
    drink_sales = drink_items.aggregate(
        s=Coalesce(Sum(F("price") * F("qty")), 0)
    )["s"]
    drink_qty = drink_items.aggregate(
        c=Coalesce(Sum("qty"), 0)
    )["c"]
    drink_unit_price = int(drink_sales // drink_qty) if drink_qty else 0

    # ―― 平均客単価 ―――――――――――――――――――――――――――――――――――
    avg_spend = int(sales_total // guest_count) if guest_count else 0

    # ── 3) カテゴリ別 breakdown (任意) ──────────────
    category_breakdown: Dict[str, int] | None = None
    if include_breakdown:
        category_breakdown = defaultdict(int)
        rows = (
            items.values(code=F("item_master__category__code"))
                 .annotate(total=Sum(F("price") * F("qty")))
        )
        for r in rows:
            category_breakdown[r["code"]] += r["total"]
        category_breakdown = dict(category_breakdown)

    # ── 4) 人件費 & 営業利益 ───────────────────────
    labor_cost = cast_payroll_sum(target_date, target_date, store_id)   # ← 1 行差し替え
    operating_profit = int(sales_total - labor_cost)

    # ── 5) 結果組み立て ───────────────────────────
    result: Dict[str, Any] = {
        "date"             : target_date.isoformat(),
        "store_id"         : store_id,
        "guest_count"      : guest_count,
        "subtotal"         : int(subtotal_sum),
        "sales_total"      : int(sales_total),
        "avg_spend"        : avg_spend,
        "drink_sales"      : int(drink_sales),
        "drink_qty"        : drink_qty,
        "drink_unit_price" : drink_unit_price,
        "extension_qty"    : extension_qty,
        "vip_ratio"        : vip_ratio,
        "labor_cost"       : int(labor_cost),
        "operating_profit" : operating_profit,
    }
    if include_breakdown:
        result["category_breakdown"] = category_breakdown

    return result
