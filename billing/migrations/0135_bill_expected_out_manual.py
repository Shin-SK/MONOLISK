from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0134_store_billing_rule'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='expected_out_manual',
            field=models.BooleanField(
                default=False,
                help_text='ユーザーが手動で expected_out を明示設定済みなら True。'
                          'True の間は auto recalc (update_expected_out) で上書きしない。',
            ),
        ),
    ]
