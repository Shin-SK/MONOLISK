from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0103_store_payroll_cutoff_day_store_payroll_cutoff_kind_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='apply_service_charge',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='bill',
            name='apply_tax',
            field=models.BooleanField(default=True),
        ),
    ]
