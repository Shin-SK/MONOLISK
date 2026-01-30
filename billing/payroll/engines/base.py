# billing/payroll/engines/base.py
from decimal import Decimal, ROUND_FLOOR
from billing.payroll.nom_pool_filter import should_exclude_from_nom_pool

class BaseEngine:
    def __init__(self, store): self.store = store

    def _pool_items_all_included(self, bill):
        """
        フェーズ2：除外判定フックを通すための土台。
        まだ除外ルールは常にFalseなので、実質 bill.items と同じ。
        """
        items = bill.items.select_related('item_master__category').all()
        return [it for it in items if not should_exclude_from_nom_pool(it)]

    def nomination_payouts(self, bill) -> dict[int, int]:
        """
        本指名パート（デフォルト＝従来の“本指名プール”）。
        店ごとに上書き可。返り値は {cast_id: amount}
        """
        totals = {}
        items_for_pool = self._pool_items_all_included(bill)
        pool_total = sum(it.subtotal for it in items_for_pool if it.is_nomination)
        if not pool_total:
            return totals

        pr = Decimal(str(self.store.nom_pool_rate or 0))
        if pr >= 1: pr /= 100
        cast_total = (Decimal(pool_total) * pr).quantize(0, rounding=ROUND_FLOOR)

        casts = list(bill.nominated_casts.all())
        if bill.main_cast and bill.main_cast not in casts:
            casts.append(bill.main_cast)

        if casts:
            each = int(cast_total // len(casts))
            for c in casts:
                totals[c.id] = totals.get(c.id, 0) + each
        return totals

    def dohan_payouts(self, bill) -> dict[int, int]:
        """
        同伴パート（デフォルト＝何もしない）。店ごとに上書き可。
        """
        return {}

    def item_payout_override(self, bill, item, stay_type: str) -> int | None:
        return None

class DefaultEngine(BaseEngine):
    pass  # Base のまま（従来どおりの本指名プール）
