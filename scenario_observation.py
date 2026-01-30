#!/usr/bin/env python
"""
Scenario観測スクリプト（コード変更禁止）
S1: Customer A 本指 → 注文 → 本指解除 → Customer B 本指 → 注文 → 締め
S2: 本指キャストだけ変更（同じ顧客）→ 注文 → 締め
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from decimal import Decimal
from billing.models import Store, Table, Cast, Bill, BillItem, ItemCategory, ItemMaster, Customer, CastPayout
from django.contrib.auth import get_user_model

User = get_user_model()

# Clean up
Bill.objects.filter(table__code__startswith="TEST").delete()
Table.objects.filter(code__startswith="TEST").delete()
Store.objects.filter(slug="test-scenario").delete()
User.objects.filter(username__startswith="test_").delete()

# Setup
store = Store.objects.create(
    slug="test-scenario",
    name="Scenario Test Store",
    nom_pool_rate=Decimal("0.50"),
    service_rate=Decimal("0"),
    tax_rate=Decimal("0"),
)
table = Table.objects.create(store=store, code="TEST-T01")

user_a = User.objects.create_user(username="test_cast_a", password="pass")
user_b = User.objects.create_user(username="test_cast_b", password="pass")
cast_a = Cast.objects.create(user=user_a, stage_name="CastA", store=store)
cast_b = Cast.objects.create(user=user_b, stage_name="CastB", store=store)

cust_a = Customer.objects.create(full_name="CustomerA", phone="090-0000-0001")
cust_b = Customer.objects.create(full_name="CustomerB", phone="090-0000-0002")

cat, _ = ItemCategory.objects.get_or_create(code="drink", defaults=dict(name="Drink", back_rate_free=Decimal("0.20")))
item, _ = ItemMaster.objects.get_or_create(store=store, code="TEST-HIGHBALL", defaults=dict(name="Highball", price_regular=3000, category=cat))

print("=" * 70)
print("SCENARIO 1: Customer A 本指 → 注文 → 本指解除 → Customer B 本指 → 注文 → 締め")
print("=" * 70)

bill = Bill.objects.create(table=table, opened_at=timezone.now())
bill.nominated_casts.add(cast_a)
bill.customers.add(cust_a)

print("\n【S1-Step1】Bill作成 + Cast A を nominated_casts に追加")
print(f"  nominated_casts IDs: {list(bill.nominated_casts.values_list('id', flat=True))}")
print(f"  is_nomination=True の BillItem数: {BillItem.objects.filter(bill=bill, is_nomination=True).count()}")

order1 = BillItem.objects.create(
    bill=bill,
    item_master=item,
    name="Highball x1",
    price=3000,
    qty=1,
    served_by_cast=cast_a,
    back_rate=Decimal("0.20"),
    is_nomination=False,
)

print("\n【S1-Step2】注文 O1 を追加（served_by_cast=CastA）")
print(f"  O1.id={order1.id}, O1.served_by_cast={order1.served_by_cast.stage_name}, O1.is_nomination={order1.is_nomination}")

bill.nominated_casts.remove(cast_a)
print("\n【S1-Step3】Cast A を nominated_casts から削除")
print(f"  nominated_casts IDs: {list(bill.nominated_casts.values_list('id', flat=True))}")

bill.nominated_casts.add(cast_b)
bill.customers.add(cust_b)
print("\n【S1-Step4】Cast B を nominated_casts に追加")
print(f"  nominated_casts IDs: {list(bill.nominated_casts.values_list('id', flat=True))}")

order2 = BillItem.objects.create(
    bill=bill,
    item_master=item,
    name="Highball x2",
    price=3000,
    qty=1,
    served_by_cast=cast_b,
    back_rate=Decimal("0.20"),
    is_nomination=False,
)
print("\n【S1-Step5】注文 O2 を追加（served_by_cast=CastB）")
print(f"  O2.id={order2.id}, O2.served_by_cast={order2.served_by_cast.stage_name}")

print("\n【S1-Step6】Bill.close() 実行")
bill.close()
bill.refresh_from_db()

print(f"\n🔍 【S1-観測】Bill 締め後:")
print(f"  subtotal={bill.subtotal}, grand_total={bill.grand_total}, total={bill.total}")

payouts = CastPayout.objects.filter(bill=bill).order_by('cast_id')
print(f"\n  CastPayout結果:")
for p in payouts:
    print(f"    {p.cast.stage_name} (id={p.cast_id}): ¥{p.amount}")

print(f"\n  Snapshot by_cast:")
if bill.payroll_snapshot:
    for bc in bill.payroll_snapshot.get('by_cast', []):
        print(f"    Cast {bc['cast_id']}: ¥{bc['amount']}")
        for bd in bc.get('breakdown', []):
            print(f"      - {bd.get('type')}: ¥{bd.get('amount')}")

print("\n" + "=" * 70)
print("SCENARIO 2: 本指キャストだけ変更（同じ顧客）→ 注文 → 締め")
print("=" * 70)

bill2 = Bill.objects.create(table=table, opened_at=timezone.now())
bill2.nominated_casts.add(cast_a)
bill2.customers.add(cust_a)

print("\n【S2-Setup】Bill2 作成 + Cast A を本指名に設定")
print(f"  nominated_casts IDs: {list(bill2.nominated_casts.values_list('id', flat=True))}")

order3 = BillItem.objects.create(
    bill=bill2,
    item_master=item,
    name="Highball x3",
    price=3000,
    qty=1,
    served_by_cast=cast_a,
    back_rate=Decimal("0.20"),
    is_nomination=False,
)
print("\n【S2-Step1】注文 O3 を追加（served_by_cast=CastA）")
print(f"  O3.id={order3.id}, O3.subtotal={order3.subtotal}")

bill2.nominated_casts.remove(cast_a)
bill2.nominated_casts.add(cast_b)
print("\n【S2-Step2】Cast A → Cast B に本指名変更（顧客A 変わらず）")
print(f"  nominated_casts IDs: {list(bill2.nominated_casts.values_list('id', flat=True))}")

print("\n【S2-Step3】Bill2.close() 実行")
bill2.close()
bill2.refresh_from_db()

print(f"\n🔍 【S2-観測】Bill2 締め後:")
print(f"  subtotal={bill2.subtotal}, grand_total={bill2.grand_total}, total={bill2.total}")

payouts2 = CastPayout.objects.filter(bill=bill2).order_by('cast_id')
print(f"\n  CastPayout結果:")
for p in payouts2:
    print(f"    {p.cast.stage_name} (id={p.cast_id}): ¥{p.amount}")

print(f"\n  Snapshot by_cast:")
if bill2.payroll_snapshot:
    for bc in bill2.payroll_snapshot.get('by_cast', []):
        print(f"    Cast {bc['cast_id']}: ¥{bc['amount']}")
        for bd in bc.get('breakdown', []):
            print(f"      - {bd.get('type')}: ¥{bd.get('amount')}")

print("\n" + "=" * 70)
print("【結論観点】")
print("=" * 70)
print("S1: 本指名を A→B に変更後に締めたら、誰が本指名パーティを受け取ったか")
print("    期待値：本指名行プールの50%が B に支払われるべき")
print("    実測値：↑")
print()
print("S2: 注文後に本指名キャストだけ A→B に変更してから締めたら")
print("    期待値：同じ顧客(A)の注文だが、本指名パーティは B に支払われるべき")
print("    実測値：↑")
