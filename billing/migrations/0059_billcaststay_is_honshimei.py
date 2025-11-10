from django.db import migrations, models

def backfill_is_honshimei(apps, schema_editor):
    BillCastStay = apps.get_model('billing', 'BillCastStay')
    # 本指名（stay_type='nom'）で在席中(left_at is null)を True に補完
    BillCastStay.objects.filter(stay_type='nom', left_at__isnull=True).update(is_honshimei=True)

class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0058_itemcategory_route_alter_itemmaster_route'),
    ]

    operations = [
        migrations.AddField(
            model_name='billcaststay',
            name='is_honshimei',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(backfill_is_honshimei, migrations.RunPython.noop),
    ]
