from django.db import migrations
from datetime import timedelta

def backfill(apps, schema_editor):
    Bill      = apps.get_model('billing', 'Bill')
    BillItem  = apps.get_model('billing', 'BillItem')
    ItemMaster= apps.get_model('billing', 'ItemMaster')

    for bill in Bill.objects.all().prefetch_related('items__item_master'):
        minutes      = 0
        base_found   = False

        for it in bill.items.all():
            master = it.item_master
            # master が無い行はスキップ
            if not master:
                continue

            code = (master.code or '').lower()
            dur  = master.duration_min or 0

            if code.startswith('set') and not base_found:
                base_found = True
                minutes += dur                     # qty は 1 行目だけ無視（=1SET）
            elif code.startswith('extension'):
                minutes += dur * it.qty

        # minutes が 0 の場合は None をセット
        bill.expected_out = (
            bill.opened_at + timedelta(minutes=minutes)
            if minutes else None
        )
        bill.save(update_fields=['expected_out'])

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0024_alter_bill_options_bill_expected_out'),
    ]
    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
