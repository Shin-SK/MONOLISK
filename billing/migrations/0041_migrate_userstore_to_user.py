from django.db import migrations

def forwards(apps, schema_editor):
    User      = apps.get_model('accounts', 'User')
    UserStore = apps.get_model('billing',  'UserStore')

    # UserStore → User.store へコピー
    for us in UserStore.objects.all():
        User.objects.filter(pk=us.user_id).update(store_id=us.store_id)

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_store'),           # ← FK 追加済み
        ('billing',  '0040_discountrule_bill_discount_rule'),  # 最新番号に合わせて
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.DeleteModel(name='UserStore'),  # もう不要なら消す
    ]
