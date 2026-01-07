from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0113_alter_storeseatsetting_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemmaster',
            name='cost',
            field=models.DecimalField(
                verbose_name='原価',
                help_text='シャンパンの歩合計算用。NULL または 0 の場合は売価を使用',
                max_digits=12,
                decimal_places=2,
                null=True,
                blank=True,
                default=None,
            ),
        ),
    ]
