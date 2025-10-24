# billing/tests/test_engine_dosukoi_dohan.py
import pytest
from decimal import Decimal
from django.utils import timezone
from billing.models import Store, Table, ItemCategory, ItemMaster, Bill, BillItem, BillCastStay, Cast
from accounts.models import User
from billing.calculator import BillCalculator
pytestmark = pytest.mark.django_db

def _setup_bill(subtotal=10000):
    store = Store.objects.create(slug="dosukoi-asa", name="どすこい", service_rate=0, tax_rate=0, nom_pool_rate=0, business_day_cutoff_hour=5)
    table = Table.objects.create(store=store, code="T01")
    u  = User.objects.create_user(username="c1", password="x")
    c1 = Cast.objects.create(user=u, stage_name="C1", store=store)
    cat  = ItemCategory.objects.create(code="drink", name="ドリンク")
    item = ItemMaster.objects.create(store=store, name="通常", price_regular=subtotal, category=cat, code="DRINK")
    bill = Bill.objects.create(table=table, opened_at=timezone.now(), main_cast=c1)
    BillItem.objects.create(bill=bill, item_master=item, qty=1)
    return bill, c1

def test_dosukoi_nom_only_20pct():
    bill, c1 = _setup_bill(10000)
    res = BillCalculator(bill).execute()
    assert sum(p.amount for p in res.cast_payouts if p.cast_id == c1.id) == 2000  # 20%

def test_dosukoi_dohan_only_30pct():
    bill, c1 = _setup_bill(10000)
    BillCastStay.objects.create(bill=bill, cast=c1, entered_at=timezone.now(), stay_type='dohan')
    res = BillCalculator(bill).execute()
    assert sum(p.amount for p in res.cast_payouts if p.cast_id == c1.id) == 3000  # 30%

def test_dosukoi_both_present_prefers_dohan():
    bill, c1 = _setup_bill(10000)
    BillCastStay.objects.create(bill=bill, cast=c1, entered_at=timezone.now(), stay_type='dohan')
    # 本指名の印（main_cast 既にあり）：同伴優先で 30% のみ
    res = BillCalculator(bill).execute()
    assert sum(p.amount for p in res.cast_payouts if p.cast_id == c1.id) == 3000
