"""
Phase 2: Bill.tables M2M migration unit tests.
Minimal tests for Serializer/QuerySet layer without API authentication.
"""
import pytest
from types import SimpleNamespace

from billing.models import Bill, Table, Store
from billing.serializers import BillSerializer
from billing.querysets import bills_in_store_qs


@pytest.mark.django_db
def test_create_bill_with_table_ids():
    """table_ids で作成 → tables M2M が設定されるか"""
    store = Store.objects.create(name="S1", slug="s1")
    tA = Table.objects.create(store=store, code="A")
    tB = Table.objects.create(store=store, code="B")
    req = SimpleNamespace(store=store, data={})
    
    ser = BillSerializer(
        data={"opened_at": "2026-02-03T10:00:00Z", "table_ids": [tA.id, tB.id]},
        context={"request": req}
    )
    assert ser.is_valid(), ser.errors
    bill = ser.save()
    
    # tables M2M に両テーブルが含まれているか確認
    atoms = sorted(bill.tables.values_list('code', flat=True))
    assert atoms == ["A", "B"], f"Expected ['A', 'B'], got {atoms}"


@pytest.mark.django_db
def test_update_bill_replace_tables():
    """table_ids で置換 → 前の M2M が消えて新しい値に置き換わるか"""
    store = Store.objects.create(name="S1", slug="s1")
    tA = Table.objects.create(store=store, code="A")
    tB = Table.objects.create(store=store, code="B")
    tC = Table.objects.create(store=store, code="C")
    
    # 初期状態: A を持つ Bill を作成
    bill = Bill.objects.create(opened_at="2026-02-03T10:00:00Z")
    bill.tables.add(tA)
    
    # Mock request with data attribute
    req_data = {"table_ids": [tB.id, tC.id]}
    req = SimpleNamespace(store=store, data=req_data)
    
    ser = BillSerializer(
        instance=bill,
        data={"table_ids": [tB.id, tC.id]},
        partial=True,
        context={"request": req}
    )
    assert ser.is_valid(), ser.errors
    bill = ser.save()
    
    # tables M2M が B, C に置き換わっているか確認
    atoms = sorted(bill.tables.values_list('code', flat=True))
    assert atoms == ["B", "C"], f"Expected ['B', 'C'], got {atoms}"


@pytest.mark.django_db
def test_bills_in_store_qs_picks_both_legacy_and_m2m():
    """bills_in_store_qs が legacy FK と M2M の両方を拾うか（NULL卓は全店共通）"""
    s1 = Store.objects.create(name="S1", slug="s1")
    s2 = Store.objects.create(name="S2", slug="s2")
    tA = Table.objects.create(store=s1, code="A")
    tB = Table.objects.create(store=s1, code="B")
    tX = Table.objects.create(store=s2, code="X")
    
    # legacy FK のみ
    b1 = Bill.objects.create(table=tA, opened_at="2026-02-03T10:00:00Z")
    
    # M2M のみ
    b2 = Bill.objects.create(opened_at="2026-02-03T10:00:00Z")
    b2.tables.add(tB)
    
    # 他店 M2M（table_id が他店卓に固定）
    b3 = Bill.objects.create(table=tX, opened_at="2026-02-03T10:00:00Z")
    
    # S1 の bills を取得
    qs = bills_in_store_qs(s1.id)
    ids = set(qs.values_list("id", flat=True))
    
    assert b1.id in ids, "legacy FK Bill should be included"
    assert b2.id in ids, "M2M Bill should be included"
    assert b3.id not in ids, "他店卓 FK Bill should be excluded"


@pytest.mark.django_db
def test_validate_table_ids_rejects_other_store():
    """validate_table_ids: 他店の table_id は拒否されるか"""
    s1 = Store.objects.create(name="S1", slug="s1")
    s2 = Store.objects.create(name="S2", slug="s2")
    tA = Table.objects.create(store=s1, code="A")
    tX = Table.objects.create(store=s2, code="X")
    
    req = SimpleNamespace(store=s1, data={})
    ser = BillSerializer(
        data={"opened_at": "2026-02-03T10:00:00Z", "table_ids": [tA.id, tX.id]},
        context={"request": req}
    )
    
    assert not ser.is_valid(), "Should reject mixed-store table_ids"
    assert "table_ids" in ser.errors, f"Expected 'table_ids' error, got {ser.errors.keys()}"
