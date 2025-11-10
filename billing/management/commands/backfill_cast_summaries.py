# billing/management/commands/backfill_cast_summaries.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import localdate
from datetime import date
from collections import defaultdict

from billing.models import Bill, CastDailySummary
from billing.calculator import BillCalculator

class Command(BaseCommand):
    """
    既に close 済みの Bill を再計算し、
    CastDailySummary を日付単位で upsert する。
       $ python manage.py backfill_cast_summaries --from 2025-08-01 --to 2025-08-31
    期間省略時は “今日” 分だけ処理。
    """

    help = "Re-create CastDailySummary from closed bills"

    def add_arguments(self, parser):
        today = localdate()
        parser.add_argument("--from", dest="date_from", default=None)
        parser.add_argument("--to",   dest="date_to",   default=None)
        
    def handle(self, *args, **opt):
        # ① 範囲を決定
        if opt["date_from"]:
            d_from = date.fromisoformat(opt["date_from"])
        else:
            # CastDailySummary が必要な一番古い日付を求める（例：最初の Bill の日）
            d_from = Bill.objects.earliest("closed_at").closed_at.date()

        if opt["date_to"]:
            d_to = date.fromisoformat(opt["date_to"])
        else:

        bills = (Bill.objects
                 .filter(closed_at__date__range=(d_from, d_to))
                 .select_related("table__store")
                 .prefetch_related("stays", "nominated_casts", "items"))

        created, updated = 0, 0
        for bill in bills:
            result = BillCalculator(bill).execute()

            # --- stay_type マップ（close 後なので left_at は無視する） ---
            stay_map = {
                s.cast_id: s.stay_type
                for s in bill.stays.all()
            }

            # --- cast_id → sales_total 集計 -------------------------------
            totals = defaultdict(int)
            for cp in result.cast_payouts:
                totals[cp.cast_id] += cp.amount

            work_date = bill.closed_at.date()
            store_id  = bill.table.store_id

            for cid, amt in totals.items():
                col = {
                    "nom":"sales_nom", "in":"sales_in", "free":"sales_free"
                }.get(stay_map.get(cid, "free"), "sales_free")

                rec, created_flag = CastDailySummary.objects.get_or_create(
                    store_id=store_id, cast_id=cid, work_date=work_date,
                    defaults={}
                )
                setattr(rec, col, (getattr(rec, col) or 0) + amt)
                rec.save(update_fields=[col])
                if created_flag: created += 1
                else:            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Backfill done. summary rows created:{created}, updated:{updated}"
        ))
