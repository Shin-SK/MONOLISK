# billing/tests/test_engine_dosukoi.py
import pytest
from decimal import Decimal
from django.utils import timezone
from billing.models import Store, Table, ItemCategory, ItemMaster, Bill, BillItem, Cast
from accounts.models import User
from billing.calculator import BillCalculator

pytestmark = pytest.mark.django_db

def test_dosukoi_honshimei_subtotal_20pct():
    store = Store.objects.create(
        slug="dosukoi-asa", name="どすこい",
        service_rate=Decimal("0"), tax_rate=Decimal("0"), nom_pool_rate=Decimal("0"),
        business_day_cutoff_hour=5,
    )
    table = Table.objects.create(store=store, code="T01")
    u  = User.objects.create_user(username="c1", password="x")
    c1 = Cast.objects.create(user=u, stage_name="本指", store=store)

    cat  = ItemCategory.objects.create(code="drink", name="ドリンク")
    item = ItemMaster.objects.create(store=store, name="通常", price_regular=10000, category=cat, code="DRINK")

    bill = Bill.objects.create(table=table, opened_at=timezone.now(), main_cast=c1)
    BillItem.objects.create(bill=bill, item_master=item, qty=1)  # 小計=10000

    res = BillCalculator(bill).execute()
    payout = sum(p.amount for p in res.cast_payouts if p.cast_id == c1.id)
    assert payout == 2000  # 10000 * 0.20
