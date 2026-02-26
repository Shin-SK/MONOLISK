# billing/payroll/engines/base.py
from decimal import Decimal, ROUND_FLOOR
from django.conf import settings
from django.utils import timezone
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
        if getattr(settings, "USE_TIMEBOXED_NOM_POOL", False):
            return self.nomination_payouts_timeboxed(bill)

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

    def nomination_payouts_timeboxed(self, bill) -> dict[int, int]:
        """
        本指名パート（時間区間×卓小計×折半）。
        Base では既存ロジックに触れず、別メソッドとして実装。
        """
        totals: dict[int, int] = {}
        now = timezone.now()

        items = bill.items.select_related('item_master__category').all()
        items_for_pool = [
            it for it in items
            if not it.exclude_from_payout and not should_exclude_from_nom_pool(it)
        ]
        if not items_for_pool:
            return totals

        pr = Decimal(str(self.store.nom_pool_rate or 0))
        if pr >= 1:
            pr /= 100

        bill_customers = bill.billcustomer_set.select_related('customer').all()
        for bc in bill_customers:
            c_start = bc.arrived_at
            if not c_start:
                continue
            c_end = bc.left_at or now
            if c_end <= c_start:
                continue

            nominations = bill.customer_nominations.filter(customer=bc.customer)
            if not nominations:
                continue

            boundaries = {c_start, c_end}
            for nom in nominations:
                n_start = max(nom.started_at, c_start)
                n_end = min(nom.ended_at or c_end, c_end)
                if n_start < n_end:
                    boundaries.add(n_start)
                    boundaries.add(n_end)

            times = sorted(t for t in boundaries if c_start <= t <= c_end)
            if len(times) < 2:
                continue

            for t_i, t_j in zip(times, times[1:]):
                if t_i >= t_j:
                    continue

                active_cast_ids = [
                    nom.cast_id for nom in nominations
                    if nom.started_at <= t_i and (nom.ended_at is None or t_i < nom.ended_at)
                ]
                active_cast_ids = list(dict.fromkeys(active_cast_ids))
                if not active_cast_ids:
                    continue

                pool_subtotal = sum(
                    it.subtotal for it in items_for_pool
                    if it.ordered_at and t_i <= it.ordered_at < t_j
                )
                if not pool_subtotal:
                    continue

                payout_total = (Decimal(pool_subtotal) * pr).quantize(0, rounding=ROUND_FLOOR)
                if not payout_total:
                    continue

                each = int(payout_total // len(active_cast_ids))
                if each <= 0:
                    continue

                for cast_id in active_cast_ids:
                    totals[cast_id] = totals.get(cast_id, 0) + each

        return totals

    def dohan_payouts(self, bill) -> dict[int, int]:
        """
        同伴パート（デフォルト＝何もしない）。店ごとに上書き可。
        """
        return {}

    def item_payout_override(self, bill, item, stay_type: str) -> int | None:
        return None

    def finalize_payroll_line(self, line, period_start, period_end):
        """
        締め処理後にPayrollRunLineを店舗固有ロジックで補正する。
        戻り値: 追加のPayrollRunBackRow リスト（空ならno-op）。
        """
        return []

class DefaultEngine(BaseEngine):
    pass  # Base のまま（従来どおりの本指名プール）
