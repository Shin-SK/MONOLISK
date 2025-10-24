# billing/payroll/engines/stores/dosukoi_asa.py
from decimal import Decimal
from .. import register
from ..base import BaseEngine

@register("dosukoi-asa")
class DosukoiAsaEngine(BaseEngine):
    RATE_NOM   = Decimal("0.20")  # 本指名 20%
    RATE_DOHAN = Decimal("0.30")  # 同伴   30%

    def _has_dohan(self, bill) -> bool:
        return bill.stays.filter(stay_type='dohan').exists()

    def _has_nom(self, bill) -> bool:
        return (
            bill.main_cast_id or
            bill.nominated_casts.exists() or
            bill.stays.filter(stay_type='nom').exists() or
            any(it.is_nomination for it in bill.items.all())
        )

    def _subtotal(self, bill) -> int:
        return sum(it.subtotal for it in bill.items.all())

    # ---- 併用不可（同伴があれば同伴のみ） ----
    def dohan_payouts(self, bill) -> dict[int, int]:
        totals = {}
        if not self._has_dohan(bill):
            return totals

        subtotal = self._subtotal(bill)
        payout   = int(Decimal(subtotal) * self.RATE_DOHAN)

        # 同伴が付いたキャスト（複数いたら均等）
        target_ids = list(bill.stays.filter(stay_type='dohan').values_list('cast_id', flat=True).distinct())
        if not target_ids:
            return totals

        each = int(payout // len(target_ids))
        for cid in target_ids:
            totals[cid] = each
        return totals

    def nomination_payouts(self, bill) -> dict[int, int]:
        # 同伴があれば“本指名は無効化”
        if self._has_dohan(bill):
            return {}

        if not self._has_nom(bill):
            return {}

        subtotal = self._subtotal(bill)
        payout   = int(Decimal(subtotal) * self.RATE_NOM)

        # main_cast がいれば全額、無ければ nominated を均等
        if bill.main_cast_id:
            return {bill.main_cast_id: payout}

        ids = list(bill.nominated_casts.values_list('id', flat=True))
        if not ids:
            return {}
        each = int(payout // len(ids))
        return {cid: each for cid in ids}
