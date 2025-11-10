from decimal import Decimal

import pytest
from django.utils import timezone

from billing.calculator import BillCalculator
from billing.models import (
    Store, Table, ItemCategory, ItemMaster, Cast, Bill, BillItem,
)


@pytest.mark.django_db
class TestBillCalculator:
    def _setup_base(self):
        """共通で使う最小データセットを構築"""
        store = Store.objects.create(
            slug="test", name="Test", service_rate=Decimal("0.10"), tax_rate=Decimal("0.10"),
            nom_pool_rate=Decimal("0.50"),
        )
        table = Table.objects.create(store=store, number=1)
        # カテゴリ
        cat_set = ItemCategory.objects.create(code="set", name="SET", back_rate_free=Decimal("0.30"))
        cat_drink = ItemCategory.objects.create(code="drink", name="Drink", back_rate_free=Decimal("0.30"))

        # アイテムマスター
        set_master = ItemMaster.objects.create(
            store=store, name="Set料金", price_regular=6000, category=cat_set, code="set"  # 60分セット
        )
        drink_master = ItemMaster.objects.create(
            store=store, name="ウーロンハイ", price_regular=2000, category=cat_drink, code="drink"
        )

        # キャスト
        user_cls = Cast._meta.get_field("user").remote_field.model
        cast_user = user_cls.objects.create(username="cast", password="pass")
        cast = Cast.objects.create(user=cast_user, stage_name="テストキャスト", store=store)

        return store, table, set_master, drink_master, cast

    def test_basic_calculation(self):
        store, table, set_master, drink_master, cast = self._setup_base()
        # Bill + Items
        bill = Bill.objects.create(table=table)
        BillItem.objects.create(bill=bill, item_master=set_master, price=6000, qty=1, served_by_cast=cast)
        BillItem.objects.create(bill=bill, item_master=drink_master, price=2000, qty=2, served_by_cast=cast)

        result = BillCalculator(bill).execute()
        # subtotal = 6000 + 4000 = 10,000
        assert result.subtotal == 10000
        # service (10%) = 1000
        assert result.service_fee == 1000
        # tax (10%) = (10000+1000)*0.1 = 1100 → floor -> 1100
        assert result.tax == 1100
        # total = 12100
        assert result.total == 12100
        # キャストバック = subtotal * 0.30 * 1 (全アイテムが free 想定)
        expected_back = int((6000 + 4000) * Decimal("0.30"))
        payout = result.cast_payouts[0]
        assert payout.amount == expected_back

    def test_nomination_pool(self):
        store, table, set_master, drink_master, cast = self._setup_base()
        # 指名料アイテムカテゴリ
        cat_nom = ItemCategory.objects.create(code="nom_fee", name="指名料", back_rate_free=Decimal("0"))
        nom_master = ItemMaster.objects.create(
            store=store, name="指名料", price_regular=3000, category=cat_nom, code="nom_fee"
        )
        bill = Bill.objects.create(table=table, main_cast=cast)
        BillItem.objects.create(bill=bill, item_master=nom_master, price=3000, qty=1, served_by_cast=cast, is_nomination=True)
        result = BillCalculator(bill).execute()
        # pool_total=3000, cast_rate=0.5 → cast_total=1500, 人数=1 → each=1500
        payout = next(p for p in result.cast_payouts if p.cast == cast)
        assert payout.amount == 1500
