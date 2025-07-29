from django.core.management.base import BaseCommand
from django.db.models import Sum, F, Q, IntegerField, ExpressionWrapper
from django.utils import timezone
from datetime import date, timedelta

from billing.models import (
    CastShift, CastPayout, CastDailySummary, Store, Cast
)

class Command(BaseCommand):
    """
    既存データを CastDailySummary に集計して書き込む。
    期間を絞りたい場合は --from / --to オプションを渡す。
    """

    help = "Back‑fill CastDailySummary from CastShift & CastPayout"

    def add_arguments(self, parser):
        parser.add_argument('--from', dest='date_from')
        parser.add_argument('--to',   dest='date_to')

    def handle(self, *args, **opts):
        date_from = (
            date.fromisoformat(opts['date_from'])
            if opts.get('date_from') else
            CastShift.objects.order_by('clock_in').values_list(
                F('clock_in__date'), flat=True).first() or date.today()
        )
        date_to = (
            date.fromisoformat(opts['date_to'])
            if opts.get('date_to') else
            timezone.now().date()
        )

        self.stdout.write(
            self.style.WARNING(
                f'Aggregating from {date_from} to {date_to} …'
            )
        )

        # ────────── 日付ループ ──────────
        cur = date_from
        bulk = []
        while cur <= date_to:
            # Cast ごと
            for cast in Cast.objects.all():
                store = cast.store
                if not store:
                    continue

                shifts = CastShift.objects.filter(
                    cast=cast, store=store,
                    clock_in__date=cur,
                )

                payouts = CastPayout.objects.filter(
                    cast=cast,
                    bill__closed_at__date=cur,
                )

                if not shifts.exists() and not payouts.exists():
                    continue  # 完全にゼロならスキップ

                worked_min = shifts.aggregate(
                    s=Sum('worked_min'))['s'] or 0
                payroll = shifts.aggregate(
                    s=Sum('payroll_amount'))['s'] or 0

                agg = payouts.aggregate(
                    free = Sum(
                        'amount',
                        filter=Q(bill_item__isnull=False)           &
                            Q(bill_item__is_nomination=False)   &
                            Q(bill_item__is_inhouse=False)
                    ) or 0,

                    inhs = Sum(
                        'amount',
                        filter=Q(bill_item__is_inhouse=True)
                    ) or 0,

                    nom  = Sum(
                        'amount',
                        filter=Q(bill_item__isnull=True) |         # プール行
                            Q(bill_item__is_nomination=True)
                    ) or 0,

                    champ = Sum(
                        'amount',
                        filter=Q(
                            bill_item__item_master__code__icontains='champ'   # ★ここを修正
                        )
                    ) or 0,
                )


                bulk.append(CastDailySummary(
                    store        = store,
                    cast         = cast,
                    work_date    = cur,
                    worked_min   = worked_min,
                    payroll      = payroll,
                    sales_free   = agg['free']  or 0,
                    sales_in     = agg['inhs']  or 0,
                    sales_nom    = agg['nom']   or 0,
                    sales_champ  = agg['champ'] or 0,
                ))

            cur += timedelta(days=1)

        CastDailySummary.objects.bulk_create(
            bulk, ignore_conflicts=True
        )
        self.stdout.write(
            self.style.SUCCESS(f'Created / updated {len(bulk)} summaries.')
        )
