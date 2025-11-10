import pytest
from decimal import Decimal
from django.utils import timezone

from billing.models import (
    Store, Table, ItemCategory, ItemMaster,
    Bill, BillItem, BillCastStay, Cast
)
from accounts.models import User
from billing.calculator import BillCalculator

pytestmark = pytest.mark.django_db

def _setup_bill(subtotal=10000):
    store = Store.objects.create(
        slug="dosukoi-asa", name="どすこい",
        service_rate=Decimal("0"), tax_rate=Decimal("0"), nom_pool_rate=Decimal("0"),
        business_day_cutoff_hour=5,
    )
    table = Table.objects.create(store=store, code="T01")
    u  = User.objects.create_user(username="c1", password="x")
    c1 = Cast.objects.create(user=u, stage_name="C1", store=store)
    cat  = ItemCategory.objects.create(code="drink", name="ドリンク")
    item = ItemMaster.objects.create(store=store, name="通常", price_regular=subtotal, category=cat, code="DRINK")
    bill = Bill.objects.create(table=table, opened_at=timezone.now(), main_cast=c1)
    BillItem.objects.create(bill=bill, item_master=item, qty=1)  # 小計=subtotal
    return bill, c1

def test_dohan_alive_30pct_only():
    """同伴が付いていると小計×30% が付与される（dosukoi, 併用不可仕様）"""
    bill, c1 = _setup_bill(10000)
    # 同伴ステイを付与
    BillCastStay.objects.create(bill=bill, cast=c1, entered_at=timezone.now(), stay_type='dohan')
    res = BillCalculator(bill).execute()
    payout = sum(p.amount for p in res.cast_payouts if p.cast_id == c1.id)
    assert payout == 3000  # 10000 * 0.30

def test_dohan_beats_nomination():
    """同伴と本指名が同時に存在しても、同伴優先（= 30%のみ）"""
    bill, c1 = _setup_bill(10000)
    # 本指名 + 同伴を両方立てても、エンジン側で同伴優先になる
    BillCastStay.objects.create(bill=bill, cast=c1, entered_at=timezone.now(), stay_type='nom')
    BillCastStay.objects.create(bill=bill, cast=c1, entered_at=timezone.now(), stay_type='dohan')
    res = BillCalculator(bill).execute()
    payout = sum(p.amount for p in res.cast_payouts if p.cast_id == c1.id)
    assert payout == 3000  # 20%+30% ではなく、同伴優先で 30%のみ
