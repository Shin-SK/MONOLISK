# Data migration to populate major_group for existing ItemCategories

from django.db import migrations


def populate_major_group(apps, schema_editor):
    """既存カテゴリを major_group で分類"""
    ItemCategory = apps.get_model('billing', 'ItemCategory')
    
    # 既存ロジックから推測されるカテゴリ分類
    MAPPINGS = {
        'set': 'set',
        'seat': 'set',
        'ext': 'extension',
        'extension': 'extension',
        'cast-drink': 'drink',
        'drink': 'drink',
        'food': 'food',
        'champagne': 'champagne',
    }
    
    # マッピングに基づいて更新
    for category in ItemCategory.objects.all():
        code = category.code.lower()
        
        # 直接マッピング
        if code in MAPPINGS:
            category.major_group = MAPPINGS[code]
        # コード接頭辞パターン（飲み物関連）
        elif any(code.startswith(p) for p in ['drink', 'wine', 'beer', 'whiskey', 'shochu', 'sake', 'brandy', 'umeshu', 'mixer', 'shot', 'softdrink']):
            category.major_group = 'drink'
        elif code.startswith('cham'):
            category.major_group = 'champagne'
        elif code.startswith('food'):
            category.major_group = 'food'
        elif code.startswith('set') or code.startswith('seat'):
            category.major_group = 'set'
        elif any(code.startswith(p) for p in ['fee', 'charge', 'tablecharge', 'nom', 'addonnight']):
            category.major_group = 'other_fee'
        else:
            # デフォルトは'other'
            category.major_group = 'other'
        
        category.save()


def reverse_major_group(apps, schema_editor):
    """rollback時に major_group をリセット"""
    ItemCategory = apps.get_model('billing', 'ItemCategory')
    for category in ItemCategory.objects.all():
        category.major_group = 'other'
        category.save()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0099_itemcategory_major_group'),
    ]

    operations = [
        migrations.RunPython(populate_major_group, reverse_major_group),
    ]

