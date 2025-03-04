# Generated by Django 5.1.6 on 2025-02-28 05:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
        ('reservation', '0006_reservationdiscrepancy'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reservation',
            name='cast_received',
        ),
        migrations.RemoveField(
            model_name='reservation',
            name='driver_received',
        ),
        migrations.RemoveField(
            model_name='reservation',
            name='store_received',
        ),
        migrations.AddField(
            model_name='reservation',
            name='membership_type',
            field=models.CharField(blank=True, choices=[('general', '一般'), ('member', 'メルマガ会員')], max_length=50, null=True, verbose_name='会員種別'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='reservation_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='予約金'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='time_minutes',
            field=models.IntegerField(blank=True, null=True, verbose_name='予約時間（分）'),
        ),
        migrations.AddField(
            model_name='reservationdiscrepancy',
            name='reservation_to_cast_diff',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='予約金→キャスト差分'),
        ),
        migrations.AddField(
            model_name='reservationdiscrepancy',
            name='reservation_to_cast_reason',
            field=models.TextField(blank=True, null=True, verbose_name='予約金→キャスト差分の理由'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='cast',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reservations_as_cast', to=settings.AUTH_USER_MODEL, verbose_name='キャスト'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='driver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reservations_as_driver', to=settings.AUTH_USER_MODEL, verbose_name='ドライバー'),
        ),
        migrations.CreateModel(
            name='StorePricing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('membership_type', models.CharField(blank=True, choices=[('general', '一般'), ('member', 'メルマガ会員')], max_length=50, null=True, verbose_name='会員種別')),
                ('time_minutes', models.IntegerField(verbose_name='時間（分）')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='料金')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reservation.course', verbose_name='対象コース')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pricings', to='account.store')),
            ],
        ),
    ]
