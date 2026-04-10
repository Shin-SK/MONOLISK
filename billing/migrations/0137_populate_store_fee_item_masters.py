"""
Data migration: Store の料金マスタ FK を既存 ItemMaster から自動紐付け。
名前完全一致（「同伴料」「本指名料」「場内指名料」）で同一 Store 内の ItemMaster を検索。
"""
from django.db import migrations


MAPPING = {
    'dohan_item_master': '同伴料',
    'main_nomination_item_master': '本指名料',
    'inhouse_nomination_item_master': '場内指名料',
}


def forwards(apps, schema_editor):
    Store = apps.get_model('billing', 'Store')
    ItemMaster = apps.get_model('billing', 'ItemMaster')

    for store in Store.objects.all():
        updated = []
        for fk_field, item_name in MAPPING.items():
            if getattr(store, f'{fk_field}_id') is not None:
                continue  # 既に設定済みならスキップ
            master = ItemMaster.objects.filter(store=store, name=item_name).first()
            if master:
                setattr(store, f'{fk_field}_id', master.id)
                updated.append(fk_field)
        if updated:
            store.save(update_fields=[f'{f}_id' for f in updated])


def backwards(apps, schema_editor):
    pass  # 巻き戻しは不要（NULL に戻すだけなので危険）


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0136_store_fee_item_masters'),
    ]
    operations = [
        migrations.RunPython(forwards, backwards),
    ]
