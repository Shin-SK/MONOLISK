"""
日次 P/L & KPI 計算ユーティリティ（キャスト人件費込み）
----------------------------------------------------------------
from datetime import date
from billing.utils.pl_daily import get_daily_pl
get_daily_pl(date(2025, 7, 25))      # 全店
get_daily_pl(date(2025, 7, 25), 1)   # Store(id=1) だけ
"""

from __future__ import annotations
from datetime import date
from decimal   import Decimal
from typing    import Dict

from django.db.models import F, Sum
from django.db.models.functions import Coalesce

from billing.models          import Bill, BillItem
from billing.utils.services  import cast_payout_sum

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
	return subtotal + service + tax


# ------------------------------------------------------------------
# public API
# ------------------------------------------------------------------
def get_daily_pl(target_date: date, store_id: int | None = None) -> Dict:
	"""指定日の P/L + KPI を dict で返す。"""

	# ── 1) 該当 Bill ─────────────────────────────
	bills = Bill.objects.filter(opened_at__date=target_date)
	if store_id:
		bills = bills.filter(table__store_id=store_id)

	sales_total = sum(
		b.total or _calc_open_bill_total(b)
		for b in bills.select_related("table__store")
	)

	# ── 2) 明細アイテム ───────────────────────────
	items = BillItem.objects.filter(bill__in=bills).select_related("item_master")

	guest_count   = items.filter(item_master__category__code="set") \
	                    .aggregate(c=Coalesce(Sum("qty"), 0))["c"]
	extension_qty = items.filter(item_master__category__code="ext") \
	                     .aggregate(c=Coalesce(Sum("qty"), 0))["c"]

	vip_set_qty   = items.filter(
		item_master__category__code="set",
		item_master__code__endswith="_vip") \
		.aggregate(c=Coalesce(Sum("qty"), 0))["c"]
	vip_ratio       = (vip_set_qty / guest_count) if guest_count else 0

	drink_items     = items.filter(item_master__category__code="drink")
	drink_sales     = drink_items.aggregate(
		s=Coalesce(Sum(F("price") * F("qty")), 0))["s"]
	drink_qty       = drink_items.aggregate(c=Coalesce(Sum("qty"), 0))["c"]
	drink_unit_price = (drink_sales // drink_qty) if drink_qty else 0

	avg_spend       = (sales_total // guest_count) if guest_count else 0

	# ── 3) キャスト人件費 & 営業利益 ───────────────
	labor_cost      = cast_payout_sum(target_date, target_date, store_id)
	operating_profit = sales_total - labor_cost

	return {
		"date"            : target_date,
		"store_id"        : store_id,
		"guest_count"     : guest_count,
		"sales_total"     : sales_total,
		"avg_spend"       : avg_spend,
		"drink_sales"     : drink_sales,
		"drink_qty"       : drink_qty,
		"drink_unit_price": drink_unit_price,
		"extension_qty"   : extension_qty,
		"vip_ratio"       : vip_ratio,
		"labor_cost"      : labor_cost,
		"operating_profit": operating_profit,
	}
