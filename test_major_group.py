#!/usr/bin/env python
"""
Test ItemCategory major_group distribution
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import ItemCategory
from django.db.models import Count

print('✅ ItemCategory.objects.count():', ItemCategory.objects.count())
print('\n✅ 大カテゴリの分布:')

for item in ItemCategory.objects.values('major_group').annotate(cnt=Count('code')).order_by('major_group'):
    print(f"  {item['major_group']}: {item['cnt']} items")

print("\n✅ サンプル確認（最初の3件）:")
for cat in ItemCategory.objects.all()[:3]:
    print(f"  {cat.code:20} -> major_group: {cat.major_group}")
