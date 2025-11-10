from django.db import migrations
from django.utils.text import slugify

def forwards(apps, schema_editor):
    DiscountRule = apps.get_model('billing', 'DiscountRule')
    for r in DiscountRule.objects.all():
        if not r.code:
            base = slugify(r.name) or f"rule-{r.pk}"
            code = base
            i = 1
            while DiscountRule.objects.filter(code=code).exclude(pk=r.pk).exists():
                i += 1
                code = f"{base}-{i}"
            r.code = code
            r.save(update_fields=['code'])

def backwards(apps, schema_editor):
    # そのまま何もしない（戻し不要）
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0063_alter_discountrule_options_discountrule_code_and_more'),
    ]
    operations = [
        migrations.RunPython(forwards, backwards),
    ]
