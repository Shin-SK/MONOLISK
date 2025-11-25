from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0084_billcaststay_is_help'),
    ]

    operations = [
        migrations.AddField(
            model_name='billitem',
            name='is_dohan',
            field=models.BooleanField(null=True, default=False),
        ),
    ]
