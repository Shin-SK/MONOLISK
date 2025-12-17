#!/usr/bin/env python
"""
Inspect ItemCategory codes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import ItemCategory

print("✅ 全ItemCategory（コード一覧）:")
for cat in ItemCategory.objects.all():
    print(f"  {cat.code:30} | {cat.name:20} | {cat.major_group}")
