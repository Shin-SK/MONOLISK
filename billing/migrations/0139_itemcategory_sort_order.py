# Generated migration: ItemCategory に sort_order 追加 + β採番で初期値投入
#
# β採番ルール:
#   - code == 'drink'           → sort_order = 10
#   - それ以外                    → name 昇順で 20, 30, 40, ... の10刻み
#     （name が同値なら code 昇順を第2キー）
#
# 既存の MenuSetting.vue catsSorted ロジック（drink最上位 + 名前昇順）を踏襲し、
# 現状の見た目を崩さない方針。

from django.db import migrations, models


def populate_sort_order(apps, schema_editor):
    """既存カテゴリに β採番で sort_order を投入"""
    ItemCategory = apps.get_model('billing', 'ItemCategory')

    all_cats = list(ItemCategory.objects.all())

    # drink と それ以外で分ける
    drink = [c for c in all_cats if (c.code or '').lower() == 'drink']
    others = [c for c in all_cats if (c.code or '').lower() != 'drink']

    # それ以外を name 昇順（name 同値は code 昇順）
    others.sort(key=lambda c: ((c.name or ''), (c.code or '')))

    # drink は 10 固定
    for c in drink:
        c.sort_order = 10
        c.save(update_fields=['sort_order'])

    # それ以外は 20 から 10 刻み
    n = 20
    for c in others:
        c.sort_order = n
        c.save(update_fields=['sort_order'])
        n += 10


def reset_sort_order(apps, schema_editor):
    """rollback 時は全部 0 に戻す"""
    ItemCategory = apps.get_model('billing', 'ItemCategory')
    ItemCategory.objects.all().update(sort_order=0)


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0138_bill_edit_log'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemcategory',
            name='sort_order',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='注文画面タブ等の並び順（昇順）。同値時は code 昇順',
                verbose_name='表示順',
            ),
        ),
        migrations.AlterModelOptions(
            name='itemcategory',
            options={'ordering': ['sort_order', 'code']},
        ),
        migrations.RunPython(populate_sort_order, reset_sort_order),
    ]
