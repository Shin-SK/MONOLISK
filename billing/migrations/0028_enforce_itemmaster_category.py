from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0027_backfill_itemmaster_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="itemmaster",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="billing.itemcategory",
                null=False,  # ここで NULL を禁止
            ),
        ),
    ]
