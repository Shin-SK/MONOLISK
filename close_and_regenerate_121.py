#!/usr/bin/env python
"""Phase 7-2c: Bill 121をクローズして再生成"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Bill
from billing.services import generate_payroll_snapshot
from django.utils import timezone

# Bill 121をクローズ
b = Bill.objects.get(id=121)
print(f'Bill 121 before:')
print(f'  closed_at: {b.closed_at}')
print(f'  has_snapshot: {bool(b.payroll_snapshot)}')

# クローズ
b.closed_at = timezone.now()
b.save(update_fields=['closed_at'])
print(f'\nBill 121 closed at: {b.closed_at}')

# スナップショット生成
snap = generate_payroll_snapshot(b)
b.payroll_snapshot = snap
b.save(update_fields=['payroll_snapshot'])
print('Snapshot generated and saved')

# 結果確認
by_cast = (b.payroll_snapshot or {}).get('by_cast', [])
print(f'\nby_cast_len: {len(by_cast)}')

total = 0
per = {}
for row in by_cast:
    cid = row.get('cast_id')
    for br in row.get('breakdown', []):
        if br.get('type') == 'nomination_pool':
            amt = int(br.get('amount') or 0)
            total += amt
            per[cid] = per.get(cid, 0) + amt

print(f'nom_pool_total: {total}')
print(f'nom_pool_per: {per}')
