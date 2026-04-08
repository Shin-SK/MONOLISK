from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0135_bill_expected_out_manual'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='dohan_item_master',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='billing.itemmaster',
                help_text='同伴料として会計に自動計上される ItemMaster',
            ),
        ),
        migrations.AddField(
            model_name='store',
            name='main_nomination_item_master',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='billing.itemmaster',
                help_text='本指名料として会計に自動計上される ItemMaster',
            ),
        ),
        migrations.AddField(
            model_name='store',
            name='inhouse_nomination_item_master',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='billing.itemmaster',
                help_text='場内指名料として会計に自動計上される ItemMaster',
            ),
        ),
    ]
