# 店舗別カテゴリ表示設定モデル (StoreCategoryPreference) の新設
#
# ・ItemCategory のグローバル値（sort_order / show_in_menu）を
#   店舗ごとに上書きできるようにするためのモデル。
# ・レコードが無い / フィールドが NULL なら ItemCategory の値を使うフォールバック方式。
# ・初期データは投入しない（未作成＝デフォルト参照）。

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0139_itemcategory_sort_order'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreCategoryPreference',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                )),
                ('sort_order', models.PositiveSmallIntegerField(
                    blank=True, null=True,
                    help_text='未設定時は ItemCategory.sort_order にフォールバック',
                    verbose_name='表示順（店舗別）',
                )),
                ('show_in_menu', models.BooleanField(
                    blank=True, null=True,
                    help_text='未設定時は ItemCategory.show_in_menu にフォールバック',
                    verbose_name='POS表示（店舗別）',
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='preferences',
                    to='billing.itemcategory',
                )),
                ('store', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='category_preferences',
                    to='billing.store',
                )),
            ],
            options={
                'verbose_name': '店舗別カテゴリ設定',
                'verbose_name_plural': '店舗別カテゴリ設定',
                'ordering': ['store', 'sort_order', 'category'],
            },
        ),
        migrations.AddConstraint(
            model_name='storecategorypreference',
            constraint=models.UniqueConstraint(
                fields=('store', 'category'),
                name='uniq_storecatpref_store_category',
            ),
        ),
    ]
