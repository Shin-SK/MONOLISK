"""Billing‑based Daily Profit & Loss utilities (simple version)

Produce daily KPI figures for a hostess‑club style store based only on the
current `Bill`/`BillItem` schema.

Public API
==========
```
from billing.utils.pl_daily import get_daily_pl
get_daily_pl(date(2025, 7, 17))          # all stores combined
get_daily_pl(date(2025, 7, 17), 1)       # only Store(id=1)
```

Return value (dict)
-------------------
key                 | description
------------------- | ----------------------------------------------
`date`              | target date (datetime.date)
`store_id`          | filtered store or *None* (all stores)
`guest_count`       | number of "set" items sold (qty sum) – proxy for guests
`sales_total`       | total revenue (¥) – uses `Bill.total` if closed, otherwise calculates with tax/service
`avg_spend`         | ⌊sales_total ÷ guest_count⌋ or 0
`drink_sales`       | total drink revenue (category == "drink")
`drink_qty`         | total drink quantity
`drink_unit_price`  | ⌊drink_sales ÷ drink_qty⌋ or 0
`extension_qty`     | total "ext" items quantity (set extensions)
`vip_ratio`         | VIP set qty ÷ all set qty (0‑1 float)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict

from django.db.models import F, Sum
from django.db.models.functions import Coalesce

from billing.models import Bill, BillItem

__all__ = ["get_daily_pl"]


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------

def _calc_open_bill_total(bill: Bill) -> int:
    """Return grand total even for *open* (total==0) bills."""
    subtotal = bill.items.aggregate(
        s=Coalesce(Sum(F("price") * F("qty")), 0)
    )["s"]

    store = bill.table.store

    sr = Decimal(store.service_rate)
    tr = Decimal(store.tax_rate)
    # interpret >=1 as percentage
    sr = sr / 100 if sr >= 1 else sr
    tr = tr / 100 if tr >= 1 else tr

    service = round(subtotal * sr)
    tax = round((subtotal + service) * tr)
    return subtotal + service + tax


# ------------------------------------------------------------
# public API
# ------------------------------------------------------------

def get_daily_pl(target_date: date, store_id: int | None = None) -> Dict:
    """Compute simple daily P/L & KPI figures."""

    # ----- relevant bills -----
    bill_qs = Bill.objects.filter(opened_at__date=target_date)
    if store_id:
        bill_qs = bill_qs.filter(table__store_id=store_id)

    # sales (grand total)
    sales_total = 0
    for b in bill_qs.select_related("table__store"):
        sales_total += b.total or _calc_open_bill_total(b)

    # ----- items queryset (prefetched once) -----
    item_qs = BillItem.objects.filter(bill__in=bill_qs).select_related("item_master")

    # guest count (set category)
    guest_count = item_qs.filter(item_master__category="set").aggregate(
        c=Coalesce(Sum("qty"), 0)
    )["c"]

    # extensions quantity
    extension_qty = item_qs.filter(item_master__category="ext").aggregate(
        c=Coalesce(Sum("qty"), 0)
    )["c"]

    # VIP ratio (code endswith "_vip")
    vip_set_qs = item_qs.filter(item_master__category="set", item_master__code__endswith="_vip")
    vip_set_qty = vip_set_qs.aggregate(c=Coalesce(Sum("qty"), 0))["c"]
    total_set_qty = guest_count or 0
    vip_ratio = (vip_set_qty / total_set_qty) if total_set_qty else 0

    # drink revenues & counts
    drink_qs = item_qs.filter(item_master__category="drink")
    drink_sales = drink_qs.aggregate(
        s=Coalesce(Sum(F("price") * F("qty")), 0)
    )["s"]
    drink_qty = drink_qs.aggregate(c=Coalesce(Sum("qty"), 0))["c"]

    drink_unit_price = (drink_sales // drink_qty) if drink_qty else 0

    avg_spend = (sales_total // guest_count) if guest_count else 0

    return {
        "date": target_date,
        "store_id": store_id,
        "guest_count": guest_count,
        "sales_total": sales_total,
        "avg_spend": avg_spend,
        "drink_sales": drink_sales,
        "drink_qty": drink_qty,
        "drink_unit_price": drink_unit_price,
        "extension_qty": extension_qty,
        "vip_ratio": vip_ratio,
    }
