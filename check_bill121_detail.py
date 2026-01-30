#!/usr/bin/env python
"""Phase 7-3d: Bill 121の詳細確認"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Bill

b = Bill.objects.get(id=121)
print(f'Bill 121 Snapshot:')
print(f'  closed_at: {b.closed_at}')
print(f'  total: {b.total}')

by_cast = (b.payroll_snapshot or {}).get('by_cast', [])
print(f'  by_cast_len: {len(by_cast)}')

# nomination_pool の合計
total = 0
per = {}
for row in by_cast:
    cid = row.get('cast_id')
    for br in row.get('breakdown', []):
        if br.get('type') == 'nomination_pool':
            amt = int(br.get('amount') or 0)
            total += amt
            per[cid] = per.get(cid, 0) + amt

print(f'  nom_pool_total: {total}')
print(f'  nom_pool_per: {per}')

# 全breakdown表示
if by_cast:
    print('\n=== Full Breakdown ===')
    for row in by_cast:
        cid = row.get('cast_id')
        stay_type = row.get('stay_type')
        amount = row.get('amount')
        print(f'\nCast {cid} (stay_type={stay_type}, total={amount}):')
        for br in row.get('breakdown', []):
            print(f'  - {br.get("label", br.get("type"))}: {br.get("amount")}')
