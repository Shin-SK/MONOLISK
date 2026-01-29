#!/usr/bin/env python
"""BillCustomer API動作チェックスクリプト"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Bill, BillCustomer
from billing.serializers_timeline import BillCustomerSerializer

# bill=117を取得
b = Bill.objects.get(id=117)
print(f"\n【Bill ID: {b.id}, pax: {b.pax}】")

# BillCustomerをクエリ
bill_customers = BillCustomer.objects.filter(bill=b).select_related("customer").order_by('id')
print(f"\n✅ クエリセットの件数: {bill_customers.count()}")

# 各BillCustomerの詳細
print("\n📋 各BillCustomerの詳細:")
for bc in bill_customers:
    cname = bc.customer.display_name if bc.customer else 'None'
    print(f"  - id={bc.id}, customer_id={bc.customer_id}, name={cname}")
    print(f"    arrived_at={bc.arrived_at}, left_at={bc.left_at}")

# シリアライズ
serializer = BillCustomerSerializer(bill_customers, many=True)
print(f"\n✅ シリアライズ後の件数: {len(serializer.data)}")

# シリアライズ後のデータ
print("\n📋 シリアライズ後のデータ:")
print(json.dumps(serializer.data, indent=2, ensure_ascii=False, default=str))

print("\n" + "="*50)
print("結論:")
if bill_customers.count() == len(serializer.data):
    print("✅ クエリとシリアライズの件数が一致 → 問題なし")
else:
    print(f"❌ 不一致: クエリ={bill_customers.count()}, シリアライズ={len(serializer.data)}")
    print("   → シリアライザに問題がある可能性")
print("="*50)
