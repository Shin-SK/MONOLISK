from django.db import migrations

SQLS = [
    # StoreSeatSetting: seat_type_tmp_id -> seat_type_id
    ("ALTER TABLE billing_storeseatsetting RENAME COLUMN seat_type_tmp_id TO seat_type_id;",
     "ALTER TABLE billing_storeseatsetting RENAME COLUMN seat_type_id TO seat_type_tmp_id;"),
    # Table: seat_type_tmp_id -> seat_type_id
    ("ALTER TABLE billing_table RENAME COLUMN seat_type_tmp_id TO seat_type_id;",
     "ALTER TABLE billing_table RENAME COLUMN seat_type_id TO seat_type_tmp_id;"),
]

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0078_seattype_stage2_swap'),  # ← 直前のステップに合わせる
    ]
    operations = [migrations.RunSQL(forward_sql, reverse_sql)
                  for forward_sql, reverse_sql in SQLS]
