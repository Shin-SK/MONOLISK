"""
Django management command: recalc_open_backrates
目的: OPEN中の BillItem で back_rate=0 となっているものを、現行ルールで再計算して更新
用法:
  python3 manage.py recalc_open_backrates --dry-run
  python3 manage.py recalc_open_backrates
  python3 manage.py recalc_open_backrates --bill-id 123
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from billing.models import BillItem, Bill
from billing.services.backrate import resolve_back_rate
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recalculate and fix back_rate for OPEN bills with back_rate=0"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Dry-run mode: show what would be updated without actually updating',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of records to update (default: no limit)',
        )
        parser.add_argument(
            '--bill-id',
            type=int,
            default=None,
            help='Process only a specific bill (useful for testing)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        limit = options.get('limit')
        bill_id = options.get('bill_id')

        self.stdout.write(self.style.SUCCESS(f"{'[DRY-RUN] ' if dry_run else ''}Starting back_rate recalculation..."))

        # 対象条件:
        # - BillItem.back_rate == 0
        # - Bill.closed_at IS NULL (OPEN中)
        # - item_master が存在（category/store解決ができる）
        queryset = BillItem.objects.filter(
            back_rate=0,
            bill__closed_at__isnull=True,
            item_master__isnull=False,
        ).select_related('bill__table__store', 'item_master__store', 'item_master__category', 'served_by_cast')

        if bill_id:
            queryset = queryset.filter(bill_id=bill_id)
            self.stdout.write(f"  Filtering for bill_id={bill_id}")

        if limit:
            queryset = queryset[:limit]

        total_count = queryset.count()
        self.stdout.write(f"  Total records with back_rate=0 in OPEN bills: {total_count}")

        updated_count = 0
        skipped_count = 0
        store_missing_count = 0

        for idx, billitem in enumerate(queryset, 1):
            try:
                # store 解決: A. bill.table.store → B. item_master.store → C. bill.store
                store = None
                if billitem.bill and hasattr(billitem.bill, 'table') and billitem.bill.table:
                    store = billitem.bill.table.store
                
                if not store and billitem.item_master:
                    store = billitem.item_master.store
                
                if not store and billitem.bill:
                    store = billitem.bill.store

                if not store:
                    store_missing_count += 1
                    logger.warning(
                        f"[recalc_open_backrates] Skipped billitem_id={billitem.id}: "
                        f"could not resolve store. bill_id={billitem.bill_id}, item_master_id={billitem.item_master_id}"
                    )
                    skipped_count += 1
                    if idx % 10 == 0:
                        self.stdout.write(f"  Processed {idx}/{total_count}...")
                    continue

                # resolve_back_rate を直接呼んで back_rate を計算
                category = billitem.item_master.category if billitem.item_master else None
                cast = billitem.served_by_cast  # None でも OK（free扱い）
                stay_type = billitem._stay_type_hint()

                new_back_rate = resolve_back_rate(
                    store=store,
                    category=category,
                    cast=cast,
                    stay_type=stay_type,
                )

                # 変更があるかチェック（不要な更新を避ける）
                if billitem.back_rate != new_back_rate:
                    if not dry_run:
                        # BillItem.save() は重いので、ここは直接 update を使う（副作用回避の王道）
                        BillItem.objects.filter(id=billitem.id).update(back_rate=new_back_rate)
                    
                    self.stdout.write(
                        f"  [{idx}/{total_count}] billitem_id={billitem.id}: "
                        f"{billitem.back_rate} → {new_back_rate} "
                        f"(bill_id={billitem.bill_id}, item={billitem.item_master.name if billitem.item_master else 'N/A'})"
                    )
                    updated_count += 1
                else:
                    skipped_count += 1

            except Exception as e:
                logger.error(
                    f"[recalc_open_backrates] Error processing billitem_id={billitem.id}: {e}",
                    exc_info=True
                )
                skipped_count += 1

            if idx % 10 == 0:
                self.stdout.write(f"  Processed {idx}/{total_count}...")

        # 最終レポート
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(f"{'[DRY-RUN] ' if dry_run else ''}Recalculation complete:")
        self.stdout.write(f"  Total records:      {total_count}")
        self.stdout.write(f"  Updated:            {updated_count}")
        self.stdout.write(f"  Skipped:            {skipped_count}")
        self.stdout.write(f"  Store missing:      {store_missing_count}")
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n⚠️  DRY-RUN MODE: No changes were actually made. "
                "Run without --dry-run to apply updates."
            ))
