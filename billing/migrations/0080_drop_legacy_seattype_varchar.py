# billing/migrations/0080_drop_legacy_seattype_varchar.py
from django.db import migrations

SQL_PG = """
DO $$
BEGIN
  -- billing_table.seat_type が残っていたら削除
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'billing_table' AND column_name = 'seat_type'
  ) THEN
    ALTER TABLE billing_table DROP COLUMN seat_type;
  END IF;

  -- billing_storeseatsetting.seat_type が残っていたら削除
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'billing_storeseatsetting' AND column_name = 'seat_type'
  ) THEN
    ALTER TABLE billing_storeseatsetting DROP COLUMN seat_type;
  END IF;
END
$$;
"""

def forwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'postgresql':
        schema_editor.execute(SQL_PG)
    else:
        # SQLite などはローカルで既に処理済みなので no-op
        # （列が残っていても次のマイグレーションで座標が合うようになっている）
        pass

def backwards(apps, schema_editor):
    # 旧カラムは復元しない（no-opでOK）
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0079_seattype_fix_db_columns'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]