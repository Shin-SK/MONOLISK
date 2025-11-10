# billing/tests/test_payout_engine.py
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from billing.models import Store, Table, ItemCategory, ItemMaster, Cast, Bill, BillItem, CastPayout
from billing.calculator import BillCalculator

User = get_user_model()

class Smoke(TestCase):
    def test_smoke(self):
        self.assertTrue(True)

class PayoutPolicyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cast1")
        self.store_ds = Store.objects.create(slug="dosukoi-asa", name="Dosukoi", service_rate=Decimal("0"), tax_rate=Decimal("0"))
        self.table_ds = Table.objects.create(store=self.store_ds, code="M01")

        self.store_other = Store.objects.create(slug="other", name="Other", service_rate=Decimal("0"), tax_rate=Decimal("0"))
        self.table_other = Table.objects.create(store=self.store_other, code="M01")

        # ドリンク：％20%、固定なし
        self.cat_drink = ItemCategory.objects.create(
            code="drink", name="Drink",
            back_rate_free=Decimal("0.20"),
            back_rate_inhouse=Decimal("0.20"),
            back_rate_nomination=Decimal("0.20"),
            use_fixed_payout_free_in=False,  # ← ％運用
        )

        # ボトル：％20%だが dosukoi では固定に上書き（カテゴリ側は固定フラグON）
        self.cat_bottle = ItemCategory.objects.create(
            code="bottle", name="Bottle",
            back_rate_free=Decimal("0.20"),
            back_rate_inhouse=Decimal("0.20"),
            back_rate_nomination=Decimal("0.20"),
            use_fixed_payout_free_in=True,   # ← 固定適用対象フラグ
        )

        self.drink_item_ds  = ItemMaster.objects.create(store=self.store_ds,  code="DRINK-1",  name="Highball",  price_regular=1000, category=self.cat_drink)
        self.bottle_item_ds = ItemMaster.objects.create(store=self.store_ds,  code="BOTTLE-1", name="Shochu",    price_regular=6000, category=self.cat_bottle)
        self.drink_item_ot  = ItemMaster.objects.create(store=self.store_other, code="DRINK-1",  name="Highball", price_regular=1000, category=self.cat_drink)
        self.bottle_item_ot = ItemMaster.objects.create(store=self.store_other, code="BOTTLE-1", name="Shochu",   price_regular=6000, category=self.cat_bottle)

        self.cast_ds = Cast.objects.create(user=self.user, stage_name="Alice", store=self.store_ds)
        self.cast_ot = Cast.objects.create(user=User.objects.create_user("cast2"), stage_name="Bob", store=self.store_other)

    def _close_and_get_payouts(self, bill: Bill):
        result = BillCalculator(bill).execute()
        bill.subtotal = result.subtotal
        bill.service_charge = result.service_fee
        bill.tax = result.tax
        bill.grand_total = result.total
        bill.total = result.total
        bill.save()
        CastPayout.objects.filter(bill=bill).delete()
        CastPayout.objects.bulk_create(result.cast_payouts)
        return list(CastPayout.objects.filter(bill=bill).order_by("cast_id"))

    def test_dosukoi_free_and_inhouse_policy(self):
        bill = Bill.objects.create(table=self.table_ds)
        BillItem.objects.create(bill=bill, item_master=self.drink_item_ds, price=1000, qty=1,
                                served_by_cast=self.cast_ds, is_nomination=False, is_inhouse=False)  # drink free -> 200
        BillItem.objects.create(bill=bill, item_master=self.bottle_item_ds, price=6000, qty=2,
                                served_by_cast=self.cast_ds, is_nomination=False, is_inhouse=False)  # bottle 500×2 -> 1000
        BillItem.objects.create(bill=bill, item_master=self.drink_item_ds, price=1000, qty=1,
                                served_by_cast=self.cast_ds, is_nomination=False, is_inhouse=True)   # drink in -> 200

        payouts = self._close_and_get_payouts(bill)
        self.assertEqual(len(payouts), 1)
        self.assertEqual(payouts[0].amount, 1400)

    def test_other_store_uses_percent_not_fixed(self):
        bill = Bill.objects.create(table=self.table_other)
        BillItem.objects.create(bill=bill, item_master=self.drink_item_ot, price=1000, qty=1,
                                served_by_cast=self.cast_ot, is_nomination=False, is_inhouse=False)  # 200
        BillItem.objects.create(bill=bill, item_master=self.bottle_item_ot, price=6000, qty=1,
                                served_by_cast=self.cast_ot, is_nomination=False, is_inhouse=False)  # 1200

        payouts = self._close_and_get_payouts(bill)
        self.assertEqual(len(payouts), 1)
        self.assertEqual(payouts[0].amount, 1400)
