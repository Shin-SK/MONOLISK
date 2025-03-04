# Generated by Django 5.1.6 on 2025-02-28 03:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservation', '0004_reservation_cast_received_reservation_driver_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='reservation.course', verbose_name='コース'),
        ),
    ]
