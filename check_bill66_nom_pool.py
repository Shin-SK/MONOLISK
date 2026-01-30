#!/usr/bin/env python
"""Phase 7-2d: Bill 66のnomination_pool確認"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Bill

b = Bill.objects.get(id=66)
by_cast = (b.payroll_snapshot or {}).get('by_cast', [])
print('by_cast_len', len(by_cast))

# nomination_pool の合計
total = 0
per = {}
for row in by_cast:
    cid = row.get('cast_id') or row.get('cast', {}).get('id')
    for br in row.get('breakdown', []):
        if br.get('type') == 'nomination_pool':
            amt = int(br.get('amount') or 0)
            total += amt
            per[cid] = per.get(cid, 0) + amt

print('nom_pool_total', total)
print('nom_pool_per', per)

# 詳細表示
if by_cast:
    print('\n=== Cast Breakdown Details ===')
    for row in by_cast:
        cid = row.get('cast_id')
        print(f"\nCast {cid}:")
        for br in row.get('breakdown', []):
            print(f"  {br.get('type')}: {br.get('amount')}")
