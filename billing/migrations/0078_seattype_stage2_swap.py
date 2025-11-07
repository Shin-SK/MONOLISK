from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0077_seattype_stage1'),  # ← 実ファイル名に合わせて
    ]

    operations = [
        # 1) 旧 文字列列 seat_type を一旦 seat_type_old に“状態上”だけリネーム
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(model_name='table', old_name='seat_type', new_name='seat_type_old'),
                migrations.RenameField(model_name='storeseatsetting', old_name='seat_type', new_name='seat_type_old'),
            ],
        ),

        # 2) 一時FK seat_type_tmp を 正式名 seat_type に“状態上”だけ昇格
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(model_name='table', old_name='seat_type_tmp', new_name='seat_type'),
                migrations.RenameField(model_name='storeseatsetting', old_name='seat_type_tmp', new_name='seat_type'),
            ],
        ),

        # 3) 旧列は「DBはそのまま・stateだけから削除」(SQLite対策)
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(model_name='table', name='seat_type_old'),
                migrations.RemoveField(model_name='storeseatsetting', name='seat_type_old'),
            ],
        ),
    ]
