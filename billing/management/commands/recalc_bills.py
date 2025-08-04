from __future__ import annotations
"""
管理コマンド: 既存 Bill を BillCalculator で一括再計算

使い方:

```
# 全店舗・全期間を一気に再計算 (推奨: 開発環境)
python manage.py recalc_bills

# 期間指定 (例: 2025-01-01 以降)
python manage.py recalc_bills --from 2025-01-01

# 店舗 slug 指定
python manage.py recalc_bills --store ginza
```

・対象 Bill は closed_at が NULL でない (= クローズ済) もののみ。
・CastPayout を削除→再生成。
・transaction.atomic() + chunked iteration でメモリ節約。
"""

import itertools
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from billing.models import Bill, CastPayout
from billing.calculator import BillCalculator

CHUNK_SIZE = 200


class Command(BaseCommand):
    help = "Recalculate existing Bills with new BillCalculator logic"

    def add_arguments(self, parser):
        parser.add_argument(
            "--store",
            help="Store slug を指定するとその店舗のみ再計算",
        )
        parser.add_argument(
            "--from",
            dest="date_from",
            help="対象期間の開始 (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--to",
            dest="date_to",
            help="対象期間の終了 (YYYY-MM-DD)。省略時は now()",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        store_slug: str | None = options.get("store")
        date_from: str | None = options.get("date_from")
        date_to: str | None = options.get("date_to") or timezone.now().date().isoformat()

        qs = Bill.objects.filter(closed_at__isnull=False)
        if store_slug:
            qs = qs.filter(table__store__slug=store_slug)
        if date_from:
            qs = qs.filter(closed_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(closed_at__date__lte=date_to)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No Bills matched the criteria."))
            return

        self.stdout.write(f"Recalculating {total} Bills…")

        processed = 0
        for chunk in _chunked_queryset(qs.order_by("id"), CHUNK_SIZE):
            with transaction.atomic():
                for bill in chunk:
                    result = BillCalculator(bill).execute()

                    # Update Bill fields
                    bill.subtotal = result.subtotal
                    bill.service_charge = result.service_fee
                    bill.tax = result.tax
                    bill.grand_total = result.total
                    bill.total = result.total if bill.settled_total is None else bill.settled_total
                    bill.save(update_fields=[
                        "subtotal",
                        "service_charge",
                        "tax",
                        "grand_total",
                        "total",
                    ])

                    # Refresh CastPayouts
                    bill.payouts.all().delete()
                    CastPayout.objects.bulk_create(result.cast_payouts)

            processed += len(chunk)
            self.stdout.write(f"  …{processed}/{total} done")

        self.stdout.write(self.style.SUCCESS("Recalculation complete!"))


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _chunked_queryset(queryset, size):
    """Yield queryset in chunks without evaluating all at once."""
    iterator = queryset.iterator(chunk_size=size)
    for first in iterator:
        yield list(itertools.chain([first], itertools.islice(iterator, size - 1)))
