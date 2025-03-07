# Generated by Django 5.1.6 on 2025-03-04 10:58

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_rank_storeuser_star_count_alter_storeuser_nickname_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storeuser',
            name='rank',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='account.rank', verbose_name='ランク'),
        ),
        migrations.AlterField(
            model_name='storeuser',
            name='star_count',
            field=models.IntegerField(default=0, verbose_name='☆数'),
        ),
        migrations.AlterField(
            model_name='storeuser',
            name='store',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.store', verbose_name='店舗'),
        ),
        migrations.AlterField(
            model_name='storeuser',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='キャスト'),
        ),
    ]
