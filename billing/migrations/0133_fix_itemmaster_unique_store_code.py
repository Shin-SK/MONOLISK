"""
古い無条件の unique_store_code 制約を削除し、
モデル定義どおりの条件付き uniq_store_code を正とする。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0132_cast_manual_subtotal"),
    ]

    operations = [
        # 古い無条件制約を削除
        migrations.RunSQL(
            sql='ALTER TABLE billing_itemmaster DROP CONSTRAINT IF EXISTS unique_store_code;',
            reverse_sql='ALTER TABLE billing_itemmaster ADD CONSTRAINT unique_store_code UNIQUE (store_id, code);',
        ),
        # モデル定義どおりの条件付き制約を作成（code が空でない場合のみ一意）
        migrations.RunSQL(
            sql=(
                'CREATE UNIQUE INDEX IF NOT EXISTS uniq_store_code '
                'ON billing_itemmaster (store_id, code) '
                "WHERE code IS NOT NULL AND code != '';"
            ),
            reverse_sql='DROP INDEX IF EXISTS uniq_store_code;',
        ),
    ]
