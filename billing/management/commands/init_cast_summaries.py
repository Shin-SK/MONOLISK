# billing/management/commands/init_cast_summaries.py
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import localdate

from billing.models import Cast, CastDailySummary, Store


class Command(BaseCommand):
    """
    CastDailySummary が **1 行も無いキャスト** だけに 0 レコードを補完する。

    ▸ 省略時は今日分だけ作成  
    ▸ --from / --to で期間を指定可
    """

    help = "Fill CastDailySummary ONLY for casts that have no summary rows yet."

    def add_arguments(self, parser):
        today = localdate()
        parser.add_argument(
            "--from", dest="date_from", default=today.isoformat(),
            help="開始日 (YYYY-MM-DD) 省略時は今日"
        )
        parser.add_argument(
            "--to", dest="date_to", default=today.isoformat(),
            help="終了日 (YYYY-MM-DD) 省略時は今日"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        d_from = date.fromisoformat(options["date_from"])
        d_to   = date.fromisoformat(options["date_to"])

        if d_from > d_to:
            self.stderr.write(self.style.ERROR("--from は --to 以前の日付にしてください"))
            return

        # ① 期間ではなく **全期間** で既にサマリーを持つキャスト ID を拾う
        existing_ids = (
            CastDailySummary.objects
            .values_list("cast_id", flat=True)
            .distinct()
        )

        # ② 1 行も持っていないキャストだけ対象
        target_casts = Cast.objects.exclude(id__in=existing_ids)

        default_store = Store.objects.get(pk=settings.DEFAULT_STORE_ID)

        delta = (d_to - d_from).days + 1
        created_cnt = 0
        skipped_no_store = 0

        for offset in range(delta):
            work_date = d_from + timedelta(days=offset)

            for cast in target_casts:
                store = cast.store or default_store
                if store is None:
                    skipped_no_store += 1
                    continue

                # ↑ cast がそもそも store を持たず、デフォルトも無いときは skip

                CastDailySummary.objects.create(
                    cast        = cast,
                    store       = store,
                    work_date   = work_date,
                    worked_min  = 0,
                    payroll     = 0,
                    sales_free  = 0,
                    sales_in    = 0,
                    sales_nom   = 0,
                    sales_champ = 0,
                )
                created_cnt += 1

        self.stdout.write(self.style.SUCCESS(
            f"CastDailySummary rows created: {created_cnt}"
        ))
        if skipped_no_store:
            self.stdout.write(
                self.style.WARNING(
                    f"Cast skipped (store 未設定): {skipped_no_store}"
                )
            )
