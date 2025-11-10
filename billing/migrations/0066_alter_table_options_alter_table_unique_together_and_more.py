from django.db import migrations, models

def copy_number_to_code(apps, schema_editor):
    Table = apps.get_model('billing', 'Table')
    for t in Table.objects.all():
        if not t.code:
            # 旧 number が int だった想定。最低限の安全化。
            try:
                t.code = str(int(getattr(t, 'number'))).zfill(2)
            except Exception:
                t.code = str(getattr(t, 'number'))
            t.save(update_fields=['code'])

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0065_discountrule_is_basic'),  # ← 実際の直前に合わせて
    ]
    operations = [
        migrations.AddField(
            model_name='table',
            name='code',
            field=models.CharField(
                max_length=16, db_index=True, null=True, blank=True,
                help_text='例: T01, B02（英数字可）'
            ),
        ),
        migrations.RunPython(copy_number_to_code, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='table',
            unique_together={('store', 'code')},
        ),
        migrations.RemoveField(
            model_name='table',
            name='number',
        ),
    ]
