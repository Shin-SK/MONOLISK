# Generated by Django 5.1.6 on 2025-02-28 04:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservation', '0005_alter_reservation_course'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReservationDiscrepancy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cast_to_driver_diff', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='キャスト→ドライバー差分')),
                ('cast_to_driver_reason', models.TextField(blank=True, null=True, verbose_name='キャスト→ドライバー差分の理由')),
                ('driver_to_store_diff', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='ドライバー→店舗差分')),
                ('driver_to_store_reason', models.TextField(blank=True, null=True, verbose_name='ドライバー→店舗差分の理由')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='記録日時')),
                ('reservation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discrepancies', to='reservation.reservation')),
            ],
        ),
    ]
