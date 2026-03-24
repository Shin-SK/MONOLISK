from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0129_add_billsubstituteitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrunline',
            name='substitute_deduction',
            field=models.PositiveIntegerField(default=0, verbose_name='立替控除'),
        ),
    ]
