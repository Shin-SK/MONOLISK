# Generated migration for adding major_group to ItemCategory

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0093_bill_pax'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemcategory',
            name='major_group',
            field=models.CharField(
                choices=[
                    ('drink', 'ドリンク'),
                    ('champagne', 'シャンパン'),
                    ('food', 'フード'),
                    ('other', 'その他商品'),
                    ('set', 'セット（人数）'),
                    ('extension', '延長'),
                    ('other_fee', 'その他料金'),
                ],
                default='other',
                help_text='集計用の大カテゴリ',
                max_length=20,
            ),
        ),
    ]
