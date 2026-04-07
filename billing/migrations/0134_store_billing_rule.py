from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0133_fix_itemmaster_unique_store_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='billing_rule',
            field=models.CharField(
                choices=[('standard', '標準'), ('garden', 'Garden')],
                default='standard',
                help_text='会計計算ルール。standard=標準、garden=Garden専用ルール（× 1.1 × 1.25, 100円未満切り上げ）',
                max_length=16,
            ),
        ),
    ]
