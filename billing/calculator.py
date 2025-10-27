from __future__ import annotations
"""
Bill / CastPayout 計算ロジック（割引フック + 席種別サービス率対応）
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import List, Dict
from billing.payroll.engines import get_engine

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

class BillCalculator:
    """伝票(Bill)を入力して金額 & CastPayout を計算する"""

    def __init__(self, bill):
        self.bill = bill
        # Table 経由で Store を取得（table が無い場合は bill.store も許容）
        self.store = bill.table.store if getattr(bill, "table_id", None) else bill.store

    # ---------------- 金額計算 ----------------
    def _subtotal_raw(self) -> Decimal:
        return Decimal(sum(it.subtotal for it in self.bill.items.all()))

    def _apply_discounts(self, subtotal: Decimal) -> Decimal:
        """DiscountRule を 1 つだけ適用（併用不可）"""
        disc = getattr(self.bill, "discount_rule", None)
        if not disc or not disc.is_active:
            return subtotal.quantize(0, rounding=ROUND_FLOOR)

        if disc.amount_off:
            subtotal = max(Decimal(0), subtotal - Decimal(disc.amount_off))
        elif disc.percent_off:
            rate = Decimal(disc.percent_off)
            # 1.00 (=100%) と 0.10 (=10%) の両方許容
            if rate >= 1:
                rate /= 100
            subtotal = subtotal * (Decimal(1) - rate)

        return subtotal.quantize(0, rounding=ROUND_FLOOR)

    def _service_fee(self, subtotal: Decimal) -> Decimal:
        """席種別の実効サービス率（Bill._effective_service_rate）を優先"""
        # Bill にヘルパがある想定（過去に追加済み）。無ければ store.service_rate を使う。
        if hasattr(self.bill, "_effective_service_rate"):
            rate = Decimal(str(self.bill._effective_service_rate()))
        else:
            rate = Decimal(str(self.store.service_rate or 0))
            if rate >= 1:
                rate /= 100
        return (subtotal * rate).quantize(0, rounding=ROUND_FLOOR)

    def _tax(self, subtotal: Decimal, service_fee: Decimal) -> Decimal:
        rate = Decimal(str(self.store.tax_rate or 0))
        if rate >= 1:
            rate /= 100
        return ((subtotal + service_fee) * rate).quantize(0, rounding=ROUND_FLOOR)

    # --------------- CastPayout ----------------
    def _cast_payouts(self):
        from .models import CastPayout
        totals = {}

        # A) 明細ごとの歩合（固定＞％）… nomination 明細は除外
        for item in self.bill.items.select_related("item_master__category", "served_by_cast"):
            if item.exclude_from_payout or not item.served_by_cast or item.is_nomination:
                continue

            cat  = getattr(getattr(item, "item_master", None), "category", None)
            stay = "in" if item.is_inhouse else "free"   # 今回は free / inhouse のみ対象
            qty  = int(item.qty or 0)
            price = int(item.price or 0)

            # ① free / inhouse で “固定バックON + 金額あり” なら 固定×数量
            if stay in ("free", "in") and cat and getattr(cat, "use_fixed_payout_free_in", False) and getattr(cat, "payout_fixed_per_item", None) is not None:
                amt = int(cat.payout_fixed_per_item) * qty
            else:
                # ② それ以外は ％（item.back_rate は 0.20 のような実数前提）
                from decimal import Decimal, ROUND_FLOOR
                amt = int((Decimal(price * qty) * Decimal(item.back_rate)).quantize(0, rounding=ROUND_FLOOR))

            if amt:
                totals[item.served_by_cast_id] = totals.get(item.served_by_cast_id, 0) + int(amt)

        # B) 店舗別：本指名
        engine = get_engine(self.store)
        for cid, add in (engine.nomination_payouts(self.bill) or {}).items():
            totals[cid] = totals.get(cid, 0) + int(add or 0)

        # C) 店舗別：同伴
        for cid, add in (engine.dohan_payouts(self.bill) or {}).items():
            totals[cid] = totals.get(cid, 0) + int(add or 0)

        # materialize（既存どおり）
        cast_objs = {c.id: c for c in self.bill.nominated_casts.all()}
        if self.bill.main_cast:
            cast_objs[self.bill.main_cast.id] = self.bill.main_cast
        for item in self.bill.items.select_related("served_by_cast"):
            if item.served_by_cast:
                cast_objs[item.served_by_cast.id] = item.served_by_cast

        return [
            CastPayout(bill=self.bill, bill_item=None, cast=cast_objs.get(cid), amount=amt)
            for cid, amt in totals.items()
            if cast_objs.get(cid)
        ]


    def execute(self):
        subtotal0 = self._subtotal_raw()
        subtotal  = self._apply_discounts(subtotal0)
        svc       = self._service_fee(subtotal)
        tax       = self._tax(subtotal, svc)
        total     = subtotal + svc + tax
        payouts   = self._cast_payouts()
        return BillCalculationResult(
            subtotal=int(subtotal),
            service_fee=int(svc),
            tax=int(tax),
            total=int(total),
            cast_payouts=payouts,
        )

    # 後方互換（古い呼び出しが .calc() の場合に備えて）
    def calc(self):
        return self.execute()