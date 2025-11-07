from django.db import migrations, models
import django.db.models.deletion

def seed_seattypes(apps, schema_editor):
    SeatType = apps.get_model('billing', 'SeatType')
    for code, name in [('main','メイン'), ('counter','カウンター'), ('box','ボックス')]:
        SeatType.objects.get_or_create(code=code, defaults={'name': name})

def map_table_codes_to_fk(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute("""
        UPDATE billing_table
           SET seat_type_tmp_id = (
                SELECT id FROM billing_seattype st WHERE st.code = billing_table.seat_type
           )
         WHERE seat_type IS NOT NULL AND seat_type <> '';
    """)

def map_storeseat_codes_to_fk(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute("""
        UPDATE billing_storeseatsetting
           SET seat_type_tmp_id = (
                SELECT id FROM billing_seattype st WHERE st.code = billing_storeseatsetting.seat_type
           )
         WHERE seat_type IS NOT NULL AND seat_type <> '';
    """)

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0076_alter_discountrule_options_and_more'),
    ]
    operations = [
        # 1) SeatType テーブルを新規作成
        migrations.CreateModel(
            name='SeatType',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('code', models.CharField(max_length=16, unique=True, db_index=True)),
                ('name', models.CharField(max_length=50)),
            ],
            options={'verbose_name':'席種','verbose_name_plural':'席種','ordering':['code']},
        ),
        # 2) 一時FK（NULL可）を追加（旧 seat_type はこの段階では削除しない！）
        migrations.AddField(
            model_name='table',
            name='seat_type_tmp',
            field=models.ForeignKey(
                to='billing.seattype',
                on_delete=django.db.models.deletion.PROTECT,
                null=True, blank=True, db_index=True),
        ),
        migrations.AddField(
            model_name='storeseatsetting',
            name='seat_type_tmp',
            field=models.ForeignKey(
                to='billing.seattype',
                on_delete=django.db.models.deletion.CASCADE,
                null=True, db_index=True),
        ),
        # 3) 初期マスター投入
        migrations.RunPython(seed_seattypes, reverse_code=migrations.RunPython.noop),
        # 4) 旧 文字列コード → 一時FK に値コピー
        migrations.RunPython(map_table_codes_to_fk, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(map_storeseat_codes_to_fk, reverse_code=migrations.RunPython.noop),
        # ※ 旧列の削除とリネームは 0078 に分ける
    ]
