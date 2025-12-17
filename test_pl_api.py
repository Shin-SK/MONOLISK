#!/usr/bin/env python
"""
Test API response with new fields
"""
import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.utils.pl_daily import get_daily_pl

# 直近の営業日のPLを取得
target_date = date.today() - timedelta(days=1)

try:
    pl_data = get_daily_pl(target_date, store_id=1)
    print("✅ PL Daily API Response:")
    for key in ['date', 'store_id', 'guest_count', 'sales_total', 'avg_spend', 
                'drink_sales', 'drink_qty', 'champagne_sales', 'champagne_qty',
                'extension_sales', 'extension_qty', 'other_sales', 
                'labor_cost', 'operating_profit']:
        val = pl_data.get(key, '🔴 MISSING')
        print(f"  {key:25} : {val}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
