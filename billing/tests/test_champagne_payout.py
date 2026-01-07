# billing/tests/test_champagne_payout.py
"""
シャンパン原価基準計算テスト
"""

from decimal import Decimal
from django.test import TestCase
from billing.models import Store, ItemCategory, ItemMaster, Bill, BillItem, Cast, Table
from django.contrib.auth import get_user_model
from billing.services.payout_helper import is_champagne, get_payout_base


class ChampagnePayoutTestCase(TestCase):
    """シャンパン原価基準計算のテストケース"""

    def setUp(self):
        # テスト用店舗
        self.store = Store.objects.create(
            name="テスト店舗",
            slug="test-shop",
        )

        # カテゴリ作成
        self.cat_champagne = ItemCategory.objects.create(
            code="champagne",
            name="シャンパン",
            major_group="champagne",
            back_rate_free=Decimal("0.30"),
        )
        self.cat_drink = ItemCategory.objects.create(
            code="drink",
            name="ドリンク",
            major_group="drink",
            back_rate_free=Decimal("0.30"),
        )

        # キャスト
        User = get_user_model()
        user = User.objects.create_user(username="cast1", password="pass")
        self.cast = Cast.objects.create(user=user, stage_name="キャスト1", store=self.store)

        # テーブル
        self.table = Table.objects.create(code="1", store=self.store)

        # 伝票
        self.bill = Bill.objects.create(table=self.table)

    def test_is_champagne_true(self):
        """シャンパン判定：True"""
        item = ItemMaster.objects.create(
            store=self.store,
            name="シャンパン2022",
            price_regular=12000,
            category=self.cat_champagne,
        )
        self.assertTrue(is_champagne(item))

    def test_is_champagne_false(self):
        """シャンパン判定：False"""
        item = ItemMaster.objects.create(
            store=self.store,
            name="ビール",
            price_regular=1000,
            category=self.cat_drink,
        )
        self.assertFalse(is_champagne(item))

    def test_payout_base_champagne_with_cost(self):
        """シャンパン原価基準：cost あり"""
        item = ItemMaster.objects.create(
            store=self.store,
            name="シャンパン2022",
            price_regular=12000,
            cost=Decimal("5000"),  # 原価 5000
            category=self.cat_champagne,
        )
        bill_item = BillItem.objects.create(
            bill=self.bill,
            item_master=item,
            qty=1,
            price=12000,
            served_by_cast=self.cast,
        )

        base, basis, value = get_payout_base(bill_item, item)
        self.assertEqual(base, Decimal("5000"))
        self.assertEqual(basis, "cost")
        self.assertEqual(value, Decimal("5000"))

    def test_payout_base_champagne_without_cost(self):
        """シャンパン原価基準：cost なし（subtotal にフォールバック）"""
        item = ItemMaster.objects.create(
            store=self.store,
            name="シャンパン2022",
            price_regular=12000,
            cost=None,  # 原価なし
            category=self.cat_champagne,
        )
        bill_item = BillItem.objects.create(
            bill=self.bill,
            item_master=item,
            qty=1,
            price=12000,
            served_by_cast=self.cast,
        )

        base, basis, value = get_payout_base(bill_item, item)
        self.assertEqual(base, Decimal("12000"))
        self.assertEqual(basis, "subtotal")
        self.assertEqual(value, Decimal("12000"))

    def test_payout_base_normal_item(self):
        """通常商品：subtotal 基準"""
        item = ItemMaster.objects.create(
            store=self.store,
            name="ビール",
            price_regular=1000,
            cost=Decimal("300"),  # cost があってもドリンクは subtotal
            category=self.cat_drink,
        )
        bill_item = BillItem.objects.create(
            bill=self.bill,
            item_master=item,
            qty=2,
            price=1000,
            served_by_cast=self.cast,
        )

        base, basis, value = get_payout_base(bill_item, item)
        self.assertEqual(base, Decimal("2000"))
        self.assertEqual(basis, "subtotal")
        self.assertEqual(value, Decimal("2000"))

    def test_calculation_champagne(self):
        """シャンパン歩合計算：原価 5000 × 30% = 1500"""
        item = ItemMaster.objects.create(
            store=self.store,
            name="シャンパン2022",
            price_regular=12000,
            cost=Decimal("5000"),
            category=self.cat_champagne,
        )
        bill_item = BillItem.objects.create(
            bill=self.bill,
            item_master=item,
            qty=1,
            price=12000,
            served_by_cast=self.cast,
            back_rate=Decimal("0.30"),
        )

        base, basis, _ = get_payout_base(bill_item, item)
        amount = int((base * Decimal("0.30")).quantize(0))
        self.assertEqual(amount, 1500)  # 5000 * 0.30 = 1500

    def test_calculation_normal_item(self):
        """通常商品歩合計算：売価 2000 × 30% = 600"""
        item = ItemMaster.objects.create(
            store=self.store,
            name="ビール",
            price_regular=1000,
            category=self.cat_drink,
        )
        bill_item = BillItem.objects.create(
            bill=self.bill,
            item_master=item,
            qty=2,
            price=1000,
            served_by_cast=self.cast,
            back_rate=Decimal("0.30"),
        )

        base, basis, _ = get_payout_base(bill_item, item)
        amount = int((base * Decimal("0.30")).quantize(0))
        self.assertEqual(amount, 600)  # 2000 * 0.30 = 600
