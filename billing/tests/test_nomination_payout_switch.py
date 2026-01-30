from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from billing.models import (
    Bill,
    BillCustomer,
    BillCustomerNomination,
    BillItem,
    Cast,
    Customer,
    ItemCategory,
    ItemMaster,
    Store,
    Table,
)
from billing.payroll.engines.base import BaseEngine


User = get_user_model()


class TestNominationSwitch(TestCase):
    def _make_dt(self, hour: int, minute: int = 0):
        tz = timezone.get_current_timezone()
        return timezone.make_aware(datetime(2026, 1, 30, hour, minute), tz)

    def _create_store_bill_customer(self):
        store = Store.objects.create(name="Test Store Switch", slug="test-switch")
        store.nom_pool_rate = Decimal("0.20")
        store.save(update_fields=["nom_pool_rate"])

        table = Table.objects.create(store=store, code="T01")
        bill = Bill.objects.create(table=table)

        customer = Customer.objects.create(full_name="Test Customer", phone="+81901230000")
        arrived_at = self._make_dt(20, 0)
        left_at = self._make_dt(21, 0)
        BillCustomer.objects.create(
            bill=bill,
            customer=customer,
            arrived_at=arrived_at,
            left_at=left_at,
        )

        return store, bill, customer, arrived_at, left_at

    def _create_cast(self, store: Store, username: str, stage_name: str):
        user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass1234")
        return Cast.objects.create(user=user, stage_name=stage_name, store=store)

    def _create_category(self):
        return ItemCategory.objects.create(
            code="drink-switch",
            name="Drink Switch",
            major_group="drink",
            exclude_from_nom_pool=False,
        )

    def _create_item_master(self, store: Store, category: ItemCategory):
        return ItemMaster.objects.create(
            store=store,
            name="Drink Item",
            price_regular=1000,
            category=category,
        )

    def _create_bill_item(self, bill: Bill, item_master: ItemMaster, subtotal: int, ordered_at):
        return BillItem.objects.create(
            bill=bill,
            item_master=item_master,
            name=item_master.name,
            price=subtotal,
            qty=1,
            ordered_at=ordered_at,
            exclude_from_payout=False,
        )

    @override_settings(USE_TIMEBOXED_NOM_POOL=True)
    def test_nomination_payouts_uses_timeboxed_when_flag_on(self):
        store, bill, customer, arrived_at, left_at = self._create_store_bill_customer()
        cast_a = self._create_cast(store, "cast_switch", "Cast A")

        BillCustomerNomination.objects.create(
            bill=bill,
            customer=customer,
            cast=cast_a,
            started_at=arrived_at,
            ended_at=left_at,
        )

        category = self._create_category()
        item_master = self._create_item_master(store, category)

        self._create_bill_item(bill, item_master, 10000, self._make_dt(20, 10))
        self._create_bill_item(bill, item_master, 2000, self._make_dt(20, 20))

        engine = BaseEngine(store)
        got = engine.nomination_payouts(bill)

        self.assertEqual(got.get(cast_a.id), 2400)
