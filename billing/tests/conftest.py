# billing/tests/conftest.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from billing.models import Bill, Table, Store, Cast, Staff, BillCastStay

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def store(db):
    return Store.objects.create(name="ジャングル東京")


@pytest.fixture
def table(store):
    return Table.objects.create(store=store, number=1)


@pytest.fixture
def bill(table):
    # opened_at などは model の default に任せる
    return Bill.objects.create(table=table)


@pytest.fixture
def cast(store):
    return Cast.objects.create(stage_name="さくら", store=store, user=User.objects.create_user("sakura"))


@pytest.fixture
def staff_user(store):
    user = User.objects.create_user("staff", password="pass")
    staff = Staff.objects.create(user=user)
    staff.stores.add(store)          # 所属店舗を付与
    return user
