# billing/management/commands/regenerate_payroll_snapshots.py
"""
既存 Bill の payroll_snapshot を再生成するコマンド。

使用例:
  python manage.py regenerate_payroll_snapshots                    # 全bill
  python manage.py regenerate_payroll_snapshots --store dosukoi-asa  # 店舗別
  python manage.py regenerate_payroll_snapshots --bill-id 123      # 特定bill
  python manage.py regenerate_payroll_snapshots --dry-run           # 実行前確認
"""

from django.core.management.base import BaseCommand, CommandError
from billing.models import Bill
from billing.payroll.snapshot import build_payroll_snapshot


class Command(BaseCommand):
    help = 'Regenerate payroll_snapshot for existing Bills (that were generated as sales copies)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--store',
            type=str,
            help='Filter by store slug (e.g., dosukoi-asa)',
        )
        parser.add_argument(
            '--bill-id',
            type=int,
            help='Regenerate specific Bill by ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without saving',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force overwrite existing snapshots (default: skip if exists)',
        )

    def handle(self, *args, **options):
        # Query condition
        qs = Bill.objects.filter(closed_at__isnull=False)
        
        if options['bill_id']:
            qs = qs.filter(id=options['bill_id'])
        elif options['store']:
            qs = qs.filter(table__store__slug=options['store'])
        
        # Filter by snapshot existence
        if not options['force']:
            qs = qs.filter(payroll_snapshot__isnull=True)
        
        count = qs.count()
        self.stdout.write(
            self.style.SUCCESS(f'Found {count} Bills to regenerate snapshot')
        )
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No Bills to process'))
            return
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - no changes will be saved'))
            for bill in qs[:5]:  # Show first 5
                self.stdout.write(f'  - Bill #{bill.id} (store={bill.table.store.slug if bill.table else "?"}, closed_at={bill.closed_at})')
            if count > 5:
                self.stdout.write(f'  ... and {count - 5} more')
            return
        
        # Regenerate snapshots
        success_count = 0
        error_count = 0
        
        for bill in qs:
            try:
                snapshot = build_payroll_snapshot(bill)
                bill.payroll_snapshot = snapshot
                bill.save(update_fields=['payroll_snapshot'])
                
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Bill #{bill.id} regenerated')
                )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Bill #{bill.id} failed: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone: {success_count} regenerated, {error_count} failed'
            )
        )
