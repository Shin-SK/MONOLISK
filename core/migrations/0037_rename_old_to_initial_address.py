# core/migrations/00XX_rename_old_to_initial_address.py
from django.db import migrations

def forwards(apps, schema_editor):
    CustomerAddress = apps.get_model('core', 'CustomerAddress')
    (CustomerAddress.objects
        .filter(label='旧住所')
        .update(label='初回住所'))

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0036_alter_reservation_status'),   # 直前の番号を指定
    ]
    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
