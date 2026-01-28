# billing/tests/test_bill_customer_sync.py
"""
Bill.pax 更新時に BillCustomer を同期するテスト。
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from accounts.models import StoreMembership
from billing.models import Bill, Table, Store, BillCustomer, Customer


User = get_user_model()


@pytest.mark.django_db
class TestBillCustomerPaxSync:
    """
    pax 更新時に BillCustomer が不足分だけ追加されることを検証。
    signals により、Bill 作成時は自動的に stub Customer が1人作成される。
    """

    def test_pax_increment_creates_billcustomers(self):
        """
        シナリオ：Bill 作成時に pax=1 で stub が1人作成される
                  その後 pax=2 に更新すると、不足分の1人が追加される
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        user = User.objects.create_user(username="testuser", password="pass")
        StoreMembership.objects.create(user=user, store=store)

        bill = Bill.objects.create(table=table, pax=1)
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1, "Bill 作成時に stub が1人作成される"

        # Act
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/billing/bills/{bill.id}/",
            {"pax": 2},
            format="json",
            HTTP_X_STORE_ID=str(store.id),
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK, f"Error: {response.content}"
        bill.refresh_from_db()
        final_count = BillCustomer.objects.filter(bill=bill).count()
        assert final_count == 2, f"BillCustomer が2件になるはず。実際: {final_count}"

    def test_pax_same_does_not_create(self):
        """
        シナリオ：pax=2 で Bill を作成すると signal で stub 1人
                  その後 pax=2 を明示的に PATCH すると、不足分 1人が追加される
                  （すでに pax に合わせて必要な顧客がいれば、この step は不要だが、
                   signals では常に 1人だけ作成されるため、ユーザーが pax を指定すると同期が動く）
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        user = User.objects.create_user(username="testuser", password="pass")
        StoreMembership.objects.create(user=user, store=store)

        bill = Bill.objects.create(table=table, pax=2)
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1, "Bill 作成時に stub が1人のみ作成される（pax値に関わらず）"

        # Act: pax=2 で PATCH すると、不足分 1人が追加される
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/billing/bills/{bill.id}/",
            {"pax": 2},
            format="json",
            HTTP_X_STORE_ID=str(store.id),
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        final_count = BillCustomer.objects.filter(bill=bill).count()
        # Bill 作成時 stub 1人 + PATCH で pax=2 に合わせる不足分 1人 = 2人
        assert final_count == 2, f"BillCustomer が2人になるはず。実際: {final_count}"

    def test_pax_decrement_does_not_delete(self):
        """
        シナリオ：pax=2 の Bill（stub 1人）を pax=1 に下げても削除しない
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        user = User.objects.create_user(username="testuser", password="pass")
        StoreMembership.objects.create(user=user, store=store)

        bill = Bill.objects.create(table=table, pax=2)
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1

        # Act
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/billing/bills/{bill.id}/",
            {"pax": 1},
            format="json",
            HTTP_X_STORE_ID=str(store.id),
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        final_count = BillCustomer.objects.filter(bill=bill).count()
        assert final_count == 1, f"BillCustomer は削除されず1件のまま。実際: {final_count}"

    def test_pax_not_in_payload_does_nothing(self):
        """
        シナリオ：pax を含まないPATCHでは同期が実行されない
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        user = User.objects.create_user(username="testuser", password="pass")
        StoreMembership.objects.create(user=user, store=store)

        bill = Bill.objects.create(table=table, pax=1)
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1

        # Act（pax なしで memo を更新）
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/billing/bills/{bill.id}/",
            {"memo": "テストメモ"},
            format="json",
            HTTP_X_STORE_ID=str(store.id),
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        final_count = BillCustomer.objects.filter(bill=bill).count()
        assert final_count == 1, f"BillCustomer が変わらず1件のまま。実際: {final_count}"

    def test_pax_increment_to_three(self):
        """
        シナリオ：pax=1 の Bill（stub 1人）を pax=3 に増やす
                  不足分の2人が追加される
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        user = User.objects.create_user(username="testuser", password="pass")
        StoreMembership.objects.create(user=user, store=store)

        bill = Bill.objects.create(table=table, pax=1)
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1

        # Act
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/billing/bills/{bill.id}/",
            {"pax": 3},
            format="json",
            HTTP_X_STORE_ID=str(store.id),
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        final_count = BillCustomer.objects.filter(bill=bill).count()
        assert final_count == 3, f"BillCustomer が3件になるはず。実際: {final_count}"

    def test_pax_increment_large_jump(self):
        """
        シナリオ：pax=1 の Bill（stub 1人）を pax=5 に一気に増やす
                  不足分の4人が追加される
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        user = User.objects.create_user(username="testuser", password="pass")
        StoreMembership.objects.create(user=user, store=store)

        bill = Bill.objects.create(table=table, pax=1)
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1

        # Act
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/billing/bills/{bill.id}/",
            {"pax": 5},
            format="json",
            HTTP_X_STORE_ID=str(store.id),
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        final_count = BillCustomer.objects.filter(bill=bill).count()
        assert final_count == 5, f"BillCustomer が5件になるはず。実際: {final_count}"

    def test_create_bill_with_pax_two(self):
        """
        シナリオ：pax=2 で Bill を作成すると、ensure_bill_customers_for_pax で2件になる
                  （signals で stub 1人 + ensure で不足分 1人）
                  perform_create の動作を模倣
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        
        # Act: pax=2 で Bill を作成
        bill = Bill.objects.create(table=table, pax=2)
        
        # signals により stub が1人作成される
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1, "signals で stub が1人作成される"
        
        # perform_create で呼ばれる ensure を手動実行
        from billing.services.bill_customer_sync import ensure_bill_customers_for_pax
        created = ensure_bill_customers_for_pax(bill)
        
        # Assert
        assert created == 1, "不足分1人が追加される"
        final_count = BillCustomer.objects.filter(bill=bill).count()
        assert final_count == 2, f"BillCustomer が2件になるはず。実際: {final_count}"

    def test_create_bill_with_pax_five(self):
        """
        シナリオ：pax=5 で Bill を作成すると、ensure_bill_customers_for_pax で5件になる
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        
        # Act: pax=5 で Bill を作成
        bill = Bill.objects.create(table=table, pax=5)
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1
        
        from billing.services.bill_customer_sync import ensure_bill_customers_for_pax
        created = ensure_bill_customers_for_pax(bill)
        
        # Assert
        assert created == 4, "不足分4人が追加される"
        final_count = BillCustomer.objects.filter(bill=bill).count()
        assert final_count == 5, f"pax=5 で BillCustomer が5件になるはず。実際: {final_count}"

    def test_create_bill_without_pax(self):
        """
        シナリオ：pax未指定（None）で Bill を作成した場合、
                  ensure_bill_customers_for_pax は何もしない（signals の stub 1人のまま）
        """
        # Arrange
        store = Store.objects.create(name="テスト店舗", slug="test-store")
        table = Table.objects.create(store=store, code="T01")
        
        # Act: pax未指定で Bill を作成
        bill = Bill.objects.create(table=table)  # pax=None
        initial_count = BillCustomer.objects.filter(bill=bill).count()
        assert initial_count == 1
        
        from billing.services.bill_customer_sync import ensure_bill_customers_for_pax
        created = ensure_bill_customers_for_pax(bill)
        
        # Assert
        assert created == 0, "pax未指定なので不足分追加なし"
        final_count = BillCustomer.objects.filter(bill=bill).count()
        assert final_count == 1, "signals の stub 1人のまま"

