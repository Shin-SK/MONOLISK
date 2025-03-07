# Generated by Django 5.1.6 on 2025-02-28 06:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservation', '0007_remove_reservation_cast_received_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Discount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='割引名')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='割引額')),
            ],
        ),
        migrations.RemoveField(
            model_name='storepricing',
            name='membership_type',
        ),
        migrations.AddField(
            model_name='reservation',
            name='enrollment_fee',
            field=models.BooleanField(default=False, verbose_name='入会金あり'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='enrollment_fee_discounted',
            field=models.BooleanField(default=True, verbose_name='入会金0円（期間限定）'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='photo_nomination_fee',
            field=models.BooleanField(default=False, verbose_name='写真指名あり'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='photo_nomination_fee_discounted',
            field=models.BooleanField(default=True, verbose_name='写真指名0円（期間限定）'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='regular_nomination_fee',
            field=models.BooleanField(default=False, verbose_name='本指名あり'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='regular_nomination_fee_discounted',
            field=models.BooleanField(default=True, verbose_name='本指名2000円（期間限定）'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='membership_type',
            field=models.CharField(choices=[('new', '新規'), ('general', '一般会員'), ('member', '本会員')], default='general', max_length=50, verbose_name='会員種別'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='discounts',
            field=models.ManyToManyField(blank=True, to='reservation.discount', verbose_name='適用割引'),
        ),
        migrations.DeleteModel(
            name='ReservationDiscrepancy',
        ),
    ]
