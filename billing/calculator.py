from __future__ import annotations
"""
Bill / CastPayout 計算ロジック（Step‑9：割引フック実装済み）
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import List, Dict

# ───────── 結果オブジェクト ─────────
@dataclass(slots=True)
class BillCalculationResult:
    subtotal: int
    service_fee: int
    tax: int
    total: int
    cast_payouts: List["CastPayout"]

    def as_dict(self) -> dict:
        return {
            "subtotal": self.subtotal,
            "service_fee": self.service_fee,
            "tax": self.tax,
            "total": self.total,
        }

# ───────── Calculator 本体 ─────────
class BillCalculator:
    """伝票(Bill)を入力して金額 & CastPayout を計算する"""

    def __init__(self, bill):
        self.bill = bill
        # Table 経由で Store を取得
        self.store = bill.table.store if getattr(bill, "table_id", None) else bill.store

    # ---------------- 金額計算 ----------------
    def _subtotal_raw(self) -> Decimal:
        return Decimal(sum(it.subtotal for it in self.bill.items.all()))

    def _apply_discounts(self, subtotal: Decimal) -> Decimal:
        """DiscountRule を 1 つだけ適用（併用不可）"""
        disc = getattr(self.bill, "discount_rule", None)
        if not disc or not disc.is_active:
            return subtotal.quantize(0, rounding=ROUND_FLOOR)

        # 固定額優先
        if disc.amount_off:
            subtotal = max(Decimal(0), subtotal - Decimal(disc.amount_off))
        elif disc.percent_off:
            rate = Decimal(disc.percent_off)
            if rate >= 1:
                rate /= 100
            subtotal = subtotal * (Decimal(1) - rate)
        return subtotal.quantize(0, rounding=ROUND_FLOOR)

    def _service_fee(self, subtotal: Decimal) -> Decimal:
        rate = Decimal(str(self.store.service_rate))
        if rate >= 1:
            rate /= 100
        return (subtotal * rate).quantize(0, rounding=ROUND_FLOOR)

    def _tax(self, subtotal: Decimal, service_fee: Decimal) -> Decimal:
        rate = Decimal(str(self.store.tax_rate))
        if rate >= 1:
            rate /= 100
        return ((subtotal + service_fee) * rate).quantize(0, rounding=ROUND_FLOOR)

    # --------------- CastPayout ----------------
    def _cast_payouts(self) -> List["CastPayout"]:
        from .models import CastPayout
        totals: Dict[int, int] = {}
        # A) アイテムバック（nomination 除外）
        for item in self.bill.items.select_related("item_master__category", "served_by_cast"):
            if item.exclude_from_payout or not item.served_by_cast or item.is_nomination:
                continue
            amt = (Decimal(item.subtotal) * item.back_rate).quantize(0, rounding=ROUND_FLOOR)
            if amt:
                totals[item.served_by_cast_id] = totals.get(item.served_by_cast_id, 0) + int(amt)
        # B) 本指名プール
        pool_total = sum(it.subtotal for it in self.bill.items.all() if it.is_nomination)
        if pool_total:
            pr = Decimal(str(self.store.nom_pool_rate))
            if pr >= 1:
                pr /= 100
            cast_total = (Decimal(pool_total) * pr).quantize(0, rounding=ROUND_FLOOR)
            casts = list(self.bill.nominated_casts.all())
            if self.bill.main_cast and self.bill.main_cast not in casts:
                casts.append(self.bill.main_cast)
            if casts:
                each = int(cast_total // len(casts))
                for c in casts:
                    totals[c.id] = totals.get(c.id, 0) + each
        # C) CastPayout objs
        cast_objs = {c.id: c for c in self.bill.nominated_casts.all()}
        if self.bill.main_cast:
            cast_objs[self.bill.main_cast.id] = self.bill.main_cast
        for item in self.bill.items.select_related("served_by_cast"):
            if item.served_by_cast:
                cast_objs[item.served_by_cast.id] = item.served_by_cast
        return [
            CastPayout(bill=self.bill, bill_item=None, cast=cast_objs[cid], amount=amt)
            for cid, amt in totals.items()
        ]

    # ---------------- 公開 API ----------------
    def execute(self) -> BillCalculationResult:
        subtotal0 = self._subtotal_raw()
        subtotal = self._apply_discounts(subtotal0)
        svc = self._service_fee(subtotal)
        tax = self._tax(subtotal, svc)
        total = subtotal + svc + tax
        payouts = self._cast_payouts()
        return BillCalculationResult(
            subtotal=int(subtotal),
            service_fee=int(svc),
            tax=int(tax),
            total=int(total),
            cast_payouts=payouts,
        )
