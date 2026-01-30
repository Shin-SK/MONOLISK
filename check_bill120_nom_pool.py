#!/usr/bin/env python
"""Phase 7-2d: Bill 120のnomination_pool確認"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Bill, BillCustomer, BillCastStay, BillCustomerNomination, BillItem

for bill_id in [119, 120, 121]:
    print(f'\n=== Bill {bill_id} ===')
    try:
        b = Bill.objects.get(id=bill_id)
        print(f'opened_at: {b.opened_at}')
        print(f'closed_at: {b.closed_at}')
        print(f'total: {b.total}')
        
        customers = BillCustomer.objects.filter(bill=b)
        print(f'customers_count: {customers.count()}')
        
        stays = BillCastStay.objects.filter(bill=b)
        print(f'stays_count: {stays.count()}')
        for stay in stays:
            print(f'  stay: cast_id={stay.cast_id}, stay_type={stay.stay_type}')
        
        items = BillItem.objects.filter(bill=b)
        print(f'items_count: {items.count()}')
        for item in items:
            print(f'  item: id={item.id}, name={item.name}, subtotal={item.subtotal}, ordered_at={item.ordered_at}')
        
        # nomination_pool確認
        by_cast = (b.payroll_snapshot or {}).get('by_cast', [])
        print(f'by_cast_len: {len(by_cast)}')
        
        total = 0
        per = {}
        for row in by_cast:
            cid = row.get('cast_id') or row.get('cast', {}).get('id')
            for br in row.get('breakdown', []):
                if br.get('type') == 'nomination_pool':
                    amt = int(br.get('amount') or 0)
                    total += amt
                    per[cid] = per.get(cid, 0) + amt
        
        print(f'nom_pool_total: {total}')
        print(f'nom_pool_per: {per}')
        
    except Exception as e:
        print(f'Error: {e}')
