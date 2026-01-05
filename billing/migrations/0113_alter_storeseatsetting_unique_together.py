# billing/migrations/0113_alter_storeseatsetting_unique_together.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0112_alter_billcustomer_unique_together_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='storeseatsetting',
                    unique_together=set(),
                ),
            ],
        ),
    ]