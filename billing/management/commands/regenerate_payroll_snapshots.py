# billing/management/commands/regenerate_payroll_snapshots.py
"""
既存 Bill の payroll_snapshot を再生成するコマンド。

使用例:
  python manage.py regenerate_payroll_snapshots --dry-run              # 全bill確認
  python manage.py regenerate_payroll_snapshots --store-slug xxx       # 店舗別
  python manage.py regenerate_payroll_snapshots --bill-id 123          # 特定bill
  python manage.py regenerate_payroll_snapshots --after 2026-01-01    # 期間指定
  python manage.py regenerate_payroll_snapshots --only-closed --limit 20  # 制限付き
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from billing.models import Bill
from billing.services import generate_payroll_snapshot
import hashlib
import json


class Command(BaseCommand):
    help = 'Regenerate payroll_snapshot for existing Bills with timeboxed logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bill-id',
            type=int,
            help='Regenerate specific Bill by ID',
        )
        parser.add_argument(
            '--store-slug',
            type=str,
            help='Filter by store slug (e.g., phase6-store-3799f6)',
        )
        parser.add_argument(
            '--after',
            type=str,
            help='Filter Bills closed after this date (YYYY-MM-DD or ISO format)',
        )
        parser.add_argument(
            '--before',
            type=str,
            help='Filter Bills closed before this date (YYYY-MM-DD or ISO format)',
        )
        parser.add_argument(
            '--only-closed',
            action='store_true',
            help='Only process closed Bills (closed_at is not null)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without saving',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of Bills to process (safety limit)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regenerate even if snapshot already exists',
        )
        parser.add_argument(
            '--stop-on-error',
            action='store_true',
            help='Stop on first error (default: skip and continue)',
        )

    def handle(self, *args, **options):
        # Build queryset
        qs = Bill.objects.all()
        
        # Apply filters
        if options['bill_id']:
            qs = qs.filter(id=options['bill_id'])
        
        if options['store_slug']:
            qs = qs.filter(table__store__slug=options['store_slug'])
        
        if options['only_closed']:
            qs = qs.filter(closed_at__isnull=False)
        
        if options['after']:
            try:
                after_date = parse_datetime(options['after'])
                if not after_date:
                    # Try simple date format
                    from datetime import datetime
                    after_date = datetime.strptime(options['after'], '%Y-%m-%d')
                qs = qs.filter(closed_at__gte=after_date)
            except Exception as e:
                raise CommandError(f'Invalid --after date format: {e}')
        
        if options['before']:
            try:
                before_date = parse_datetime(options['before'])
                if not before_date:
                    from datetime import datetime
                    before_date = datetime.strptime(options['before'], '%Y-%m-%d')
                qs = qs.filter(closed_at__lt=before_date)
            except Exception as e:
                raise CommandError(f'Invalid --before date format: {e}')
        
        # Order by closed_at for predictable processing
        qs = qs.order_by('-closed_at')
        
        # Apply limit (must be after order_by)
        if options['limit']:
            qs = qs[:options['limit']]
        
        count = qs.count()
        self.stdout.write(
            self.style.SUCCESS(f'Found {count} Bills to process')
        )
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No Bills match the filters'))
            return
        
        # Dry-run mode
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - no changes will be saved\n'))
            self.stdout.write('Target Bills:')
            for i, bill in enumerate(qs[:10], 1):
                store_slug = bill.table.store.slug if bill.table and bill.table.store else '?'
                closed = bill.closed_at.strftime('%Y-%m-%d %H:%M') if bill.closed_at else 'open'
                has_snap = '✓' if bill.payroll_snapshot else '✗'
                self.stdout.write(
                    f'  {i}. Bill #{bill.id} | store={store_slug} | closed={closed} | snapshot={has_snap}'
                )
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
            return
        
        # Confirm before processing
        if count > 10 and not options['bill_id']:
            self.stdout.write(
                self.style.WARNING(
                    f'\nAbout to regenerate snapshots for {count} Bills.'
                )
            )
            confirm = input('Continue? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted'))
                return
        
        # Process Bills
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        self.stdout.write('\nProcessing...\n')
        
        for i, bill in enumerate(qs, 1):
            try:
                # Get store info
                store_slug = bill.table.store.slug if bill.table and bill.table.store else 'unknown'
                
                # Check if snapshot exists
                if bill.payroll_snapshot and not options['force']:
                    skipped_count += 1
                    if options.get('verbosity', 1) >= 2:
                        self.stdout.write(
                            self.style.WARNING(f'  {i}/{count} Bill #{bill.id} - skipped (snapshot exists)')
                        )
                    continue
                
                # Get old hash
                old_hash = None
                if bill.payroll_snapshot:
                    old_hash = bill.payroll_snapshot.get('hash', '?')[:16]
                
                # Regenerate snapshot
                snapshot = generate_payroll_snapshot(bill)
                
                # Get new hash
                new_hash = snapshot.get('hash', '?')[:16]
                
                # Check if changed
                changed = old_hash != new_hash
                
                # Save
                bill.payroll_snapshot = snapshot
                bill.save(update_fields=['payroll_snapshot'])
                
                success_count += 1
                
                # Progress log
                change_mark = '✎' if changed else '='
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  {i}/{count} {change_mark} Bill #{bill.id} | store={store_slug} | '
                        f'{old_hash or "none"} → {new_hash}'
                    )
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  {i}/{count} ✗ Bill #{bill.id} - ERROR: {str(e)}')
                )
                
                if options['stop_on_error']:
                    raise CommandError(f'Stopped on error at Bill #{bill.id}: {e}')
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'Done: {success_count} regenerated, {skipped_count} skipped, {error_count} failed'
            )
        )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    '\nSome Bills failed to regenerate. Check errors above.'
                )
            )
