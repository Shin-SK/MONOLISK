from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

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


class TestNominationPayoutTimeboxedBase(TestCase):
    def _make_dt(self, hour: int, minute: int = 0):
        tz = timezone.get_current_timezone()
        return timezone.make_aware(datetime(2026, 1, 30, hour, minute), tz)

    def _create_store_bill_customer(self):
        store = Store.objects.create(name="Test Store", slug="test-store")
        store.nom_pool_rate = Decimal("0.20")
        store.save(update_fields=["nom_pool_rate"])

        table = Table.objects.create(store=store, code="T01")
        bill = Bill.objects.create(table=table)

        customer = Customer.objects.create(full_name="Test Customer", phone="+81901234567")
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

    def _create_category(self, code: str, name: str, exclude_from_nom_pool: bool = False):
        return ItemCategory.objects.create(
            code=code,
            name=name,
            major_group="drink",
            exclude_from_nom_pool=exclude_from_nom_pool,
        )

    def _create_item_master(self, store: Store, category: ItemCategory, name: str):
        return ItemMaster.objects.create(
            store=store,
            name=name,
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

    def test_single_customer_single_cast_basic(self):
        store, bill, customer, arrived_at, left_at = self._create_store_bill_customer()
        cast_a = self._create_cast(store, "cast_a", "Cast A")

        BillCustomerNomination.objects.create(
            bill=bill,
            customer=customer,
            cast=cast_a,
            started_at=arrived_at,
            ended_at=left_at,
        )

        category = self._create_category(code="drink", name="Drink", exclude_from_nom_pool=False)
        item_master = self._create_item_master(store, category, name="Drink Item")

        self._create_bill_item(bill, item_master, 10000, self._make_dt(20, 10))
        self._create_bill_item(bill, item_master, 2000, self._make_dt(20, 20))

        engine = BaseEngine(store)
        totals = engine.nomination_payouts_timeboxed(bill)

        assert totals == {cast_a.id: 2400}

    def test_nomination_switch_no_rollover(self):
        store, bill, customer, arrived_at, left_at = self._create_store_bill_customer()
        cast_a = self._create_cast(store, "cast_a2", "Cast A")
        cast_b = self._create_cast(store, "cast_b2", "Cast B")

        BillCustomerNomination.objects.create(
            bill=bill,
            customer=customer,
            cast=cast_a,
            started_at=arrived_at,
            ended_at=self._make_dt(20, 30),
        )
        BillCustomerNomination.objects.create(
            bill=bill,
            customer=customer,
            cast=cast_b,
            started_at=self._make_dt(20, 30),
            ended_at=left_at,
        )

        category = self._create_category(code="drink2", name="Drink2", exclude_from_nom_pool=False)
        item_master = self._create_item_master(store, category, name="Drink Item 2")

        self._create_bill_item(bill, item_master, 10000, self._make_dt(20, 10))
        self._create_bill_item(bill, item_master, 2000, self._make_dt(20, 40))

        engine = BaseEngine(store)
        totals = engine.nomination_payouts_timeboxed(bill)

        assert totals == {cast_a.id: 2000, cast_b.id: 400}

    def test_multiple_casts_split_evenly(self):
        store, bill, customer, arrived_at, left_at = self._create_store_bill_customer()
        cast_a = self._create_cast(store, "cast_a3", "Cast A")
        cast_b = self._create_cast(store, "cast_b3", "Cast B")

        BillCustomerNomination.objects.create(
            bill=bill,
            customer=customer,
            cast=cast_a,
            started_at=arrived_at,
            ended_at=left_at,
        )
        BillCustomerNomination.objects.create(
            bill=bill,
            customer=customer,
            cast=cast_b,
            started_at=arrived_at,
            ended_at=left_at,
        )

        category = self._create_category(code="drink3", name="Drink3", exclude_from_nom_pool=False)
        item_master = self._create_item_master(store, category, name="Drink Item 3")

        self._create_bill_item(bill, item_master, 10000, self._make_dt(20, 10))

        engine = BaseEngine(store)
        totals = engine.nomination_payouts_timeboxed(bill)

        assert totals == {cast_a.id: 1000, cast_b.id: 1000}

    def test_exclude_from_nom_pool_category(self):
        store, bill, customer, arrived_at, left_at = self._create_store_bill_customer()
        cast_a = self._create_cast(store, "cast_a4", "Cast A")

        BillCustomerNomination.objects.create(
            bill=bill,
            customer=customer,
            cast=cast_a,
            started_at=arrived_at,
            ended_at=left_at,
        )

        category_tc = self._create_category(code="tc", name="TC", exclude_from_nom_pool=True)
        category_normal = self._create_category(code="drink4", name="Drink4", exclude_from_nom_pool=False)
        item_master_tc = self._create_item_master(store, category_tc, name="TC Item")
        item_master_normal = self._create_item_master(store, category_normal, name="Drink Item 4")

        self._create_bill_item(bill, item_master_tc, 2000, self._make_dt(20, 10))
        self._create_bill_item(bill, item_master_normal, 10000, self._make_dt(20, 20))

        engine = BaseEngine(store)
        totals = engine.nomination_payouts_timeboxed(bill)

        assert totals == {cast_a.id: 2000}
