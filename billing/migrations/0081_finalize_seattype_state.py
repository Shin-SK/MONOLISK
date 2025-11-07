from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0080_drop_legacy_seattype_varchar'),  # 直前に合わせる
    ]
    operations = [
        # DBは既に正しい（seat_type_id のみ）。状態だけユニーク制約を確定。
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='storeseatsetting',
                    unique_together={('store', 'seat_type')},
                ),
            ],
        ),
    ]