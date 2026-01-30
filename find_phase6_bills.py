#!/usr/bin/env python
"""Phase 7-2: phase6-storeのBillを探す"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Bill, BillCustomer, BillCastStay
from accounts.models import StoreMembership

# phase6-store のBillを探す
print('=== Phase 6 Store Bills ===')
# storeのslugから検索
# StoreMembershipからstoreを探す
try:
    # Billからstoreを探す方法を確認
    bills = Bill.objects.all()[:5]
    print(f'Total bills: {Bill.objects.count()}')
    
    # BillからStore情報を探す
    for b in bills:
        print(f'Bill {b.id} fields:', [f.name for f in b._meta.get_fields() if not f.name.startswith('_')][:10])
        break
    
    # Phase 6で作成されたBillは opened_at が最近
    recent_bills = Bill.objects.filter(opened_at__gte='2026-01-30').order_by('-opened_at')[:10]
    print(f'\n=== Bills created on 2026-01-30 ===')
    for b in recent_bills:
        customers_count = BillCustomer.objects.filter(bill=b).count()
        stays_count = BillCastStay.objects.filter(bill=b).count()
        print(f'Bill {b.id}: opened={b.opened_at.strftime("%Y-%m-%d %H:%M:%S")}, '
              f'closed={b.closed_at.strftime("%Y-%m-%d %H:%M:%S") if b.closed_at else "None"}, '
              f'customers={customers_count}, stays={stays_count}, '
              f'has_snapshot={bool(b.payroll_snapshot)}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
