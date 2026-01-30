#!/usr/bin/env python
"""Phase 7-2: Bill確認スクリプト"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Bill, BillCastStay, BillCustomer, BillCustomerNomination, BillItem

# Bill 66 確認
print('=== Bill 66 ===')
try:
    b66 = Bill.objects.get(id=66)
    print('opened_at:', b66.opened_at)
    print('closed_at:', b66.closed_at)
    print('total:', b66.total)
    stays = BillCastStay.objects.filter(bill=b66).count()
    print('stays_count:', stays)
    customers = BillCustomer.objects.filter(bill=b66).count()
    print('customers_count:', customers)
    items = BillItem.objects.filter(bill=b66).count()
    print('items_count:', items)
    print('has_snapshot:', bool(b66.payroll_snapshot))
except Exception as e:
    print('Error:', e)

print()
print('=== Bill 126 ===')
try:
    b126 = Bill.objects.get(id=126)
    print('opened_at:', b126.opened_at)
    print('closed_at:', b126.closed_at)
    print('total:', b126.total)
    stays = BillCastStay.objects.filter(bill=b126).count()
    print('stays_count:', stays)
    customers = BillCustomer.objects.filter(bill=b126).count()
    print('customers_count:', customers)
    items = BillItem.objects.filter(bill=b126).count()
    print('items_count:', items)
    print('has_snapshot:', bool(b126.payroll_snapshot))
except Exception as e:
    print('Error:', e)

print()
print('=== Bills with closed_at AND nominations (recent 10) ===')
bills = Bill.objects.exclude(closed_at__isnull=True).order_by('-closed_at')[:20]
count = 0
for b in bills:
    stays_count = BillCastStay.objects.filter(bill=b).count()
    customers_count = BillCustomer.objects.filter(bill=b).count()
    if customers_count > 0 and stays_count > 0:
        count += 1
        print(f'Bill {b.id}: closed={b.closed_at.strftime("%Y-%m-%d %H:%M") if b.closed_at else "None"}, '
              f'total={b.total}, stays={stays_count}, customers={customers_count}, '
              f'has_snapshot={bool(b.payroll_snapshot)}')
        if count >= 10:
            break
