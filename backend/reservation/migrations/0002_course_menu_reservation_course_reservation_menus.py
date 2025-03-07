# Generated by Django 5.1.6 on 2025-02-27 12:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='コース名')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='料金')),
            ],
        ),
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='メニュー名')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='料金')),
            ],
        ),
        migrations.AddField(
            model_name='reservation',
            name='course',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='reservation.course', verbose_name='コース'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='menus',
            field=models.ManyToManyField(blank=True, to='reservation.menu', verbose_name='メニュー'),
        ),
    ]
