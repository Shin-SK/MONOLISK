"""
Tests for BillCustomer timeline and BillCustomerNomination
"""
import pytest
from datetime import datetime, timedelta
from django.utils import timezone

from billing.models import Bill, BillCustomer, BillCustomerNomination, Store, Customer, Cast, Table
from accounts.models import User


@pytest.mark.django_db
class TestBillCustomerTimeline:
    """BillCustomer の arrived_at / left_at テスト"""
    
    @pytest.fixture
    def bill_with_customer(self):
        """テスト用伝票と顧客"""
        store = Store.objects.create(name='Test Store', slug='test-store')
        table = Table.objects.create(store=store, code='T01')
        bill = Bill.objects.create(table=table)
        customer = Customer.objects.create(full_name='Test Customer', phone='+81901234567')
        bill_customer = BillCustomer.objects.create(bill=bill, customer=customer)
        
        return {
            'bill': bill,
            'customer': customer,
            'bill_customer': bill_customer,
            'store': store,
        }
    
    def test_billcustomer_create_with_arrived_at(self, bill_with_customer):
        """arrived_at を設定して BillCustomer を作成"""
        arrived = timezone.now()
        bc = bill_with_customer['bill_customer']
        bc.arrived_at = arrived
        bc.save()
        
        refreshed = BillCustomer.objects.get(id=bc.id)
        assert refreshed.arrived_at == arrived
        assert refreshed.left_at is None
    
    def test_billcustomer_create_with_arrived_and_left(self, bill_with_customer):
        """arrived_at と left_at の両方を設定"""
        bc = bill_with_customer['bill_customer']
        arrived = timezone.now()
        left = arrived + timedelta(hours=2)
        
        bc.arrived_at = arrived
        bc.left_at = left
        bc.save()
        
        refreshed = BillCustomer.objects.get(id=bc.id)
        assert refreshed.arrived_at == arrived
        assert refreshed.left_at == left
    
    def test_billcustomer_constraint_left_before_arrived(self, bill_with_customer):
        """left_at < arrived_at は DB 制約で弾かれる"""
        from django.db import IntegrityError
        
        bc = bill_with_customer['bill_customer']
        arrived = timezone.now()
        left = arrived - timedelta(hours=1)
        
        bc.arrived_at = arrived
        bc.left_at = left
        
        with pytest.raises(IntegrityError):
            bc.save()
    
    def test_billcustomer_partial_update_arrived_at(self, bill_with_customer):
        """既存の BillCustomer に arrived_at を追加"""
        bc = bill_with_customer['bill_customer']
        arrived = timezone.now()
        bc.arrived_at = arrived
        bc.save()
        
        left = arrived + timedelta(hours=1)
        bc.left_at = left
        bc.save()
        
        refreshed = BillCustomer.objects.get(id=bc.id)
        assert refreshed.arrived_at == arrived
        assert refreshed.left_at == left
    
    def test_billcustomer_both_null(self, bill_with_customer):
        """arrived_at も left_at も null のまま保存"""
        bc = bill_with_customer['bill_customer']
        bc.arrived_at = None
        bc.left_at = None
        bc.save()
        
        refreshed = BillCustomer.objects.get(id=bc.id)
        assert refreshed.arrived_at is None
        assert refreshed.left_at is None
    
    def test_billcustomer_auto_arrived_at_on_create(self):
        """arrived_at 未指定で BillCustomer を作成したとき、自動で現在時刻が入る"""
        store = Store.objects.create(name='Test Store', slug='test-store')
        table = Table.objects.create(store=store, code='T01')
        bill = Bill.objects.create(table=table)
        customer = Customer.objects.create(full_name='Auto Arrived Customer', phone='+81901234999')
        
        # arrived_at を指定せずに作成
        bc = BillCustomer.objects.create(bill=bill, customer=customer)
        
        # arrived_at が自動で入っていることを確認
        assert bc.arrived_at is not None
        # 作成時刻から1秒以内であることを確認（妥当性チェック）
        now = timezone.now()
        assert abs((bc.arrived_at - now).total_seconds()) < 1


@pytest.mark.django_db
class TestBillCustomerNomination:
    """BillCustomerNomination の作成・検証テスト"""
    
    @pytest.fixture
    def bill_with_customers_and_casts(self):
        """テスト用の bill, customers, casts を作成"""
        store = Store.objects.create(name='Test Store', slug='test-store')
        other_store = Store.objects.create(name='Other Store', slug='other-store')
        
        table = Table.objects.create(store=store, code='T01')
        bill = Bill.objects.create(table=table)
        
        # 顧客を2人作成
        customer1 = Customer.objects.create(full_name='Customer 1', phone='+81901234567')
        customer2 = Customer.objects.create(full_name='Customer 2', phone='+81901234568')
        
        # BillCustomer を作成
        BillCustomer.objects.create(bill=bill, customer=customer1)
        BillCustomer.objects.create(bill=bill, customer=customer2)
        
        # キャストを作成
        cast_user1 = User.objects.create_user(username='cast1', password='pass')
        cast_user2 = User.objects.create_user(username='cast2', password='pass')
        cast_user_other = User.objects.create_user(username='cast_other', password='pass')
        
        cast1 = Cast.objects.create(user=cast_user1, stage_name='Cast 1', store=store)
        cast2 = Cast.objects.create(user=cast_user2, stage_name='Cast 2', store=store)
        cast_other = Cast.objects.create(user=cast_user_other, stage_name='Cast Other', store=other_store)
        
        return {
            'bill': bill,
            'customer1': customer1,
            'customer2': customer2,
            'cast1': cast1,
            'cast2': cast2,
            'cast_other': cast_other,
            'store': store,
            'other_store': other_store,
        }
    
    def test_nomination_create_valid(self, bill_with_customers_and_casts):
        """有効な BillCustomerNomination を作成"""
        d = bill_with_customers_and_casts
        nomination = BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        assert nomination.bill == d['bill']
        assert nomination.customer == d['customer1']
        assert nomination.cast == d['cast1']
        assert nomination.created_at is not None
    
    def test_nomination_unique_constraint(self, bill_with_customers_and_casts):
        """同じ (bill, customer, cast) の組み合わせは作成できない"""
        from django.db import IntegrityError
        
        d = bill_with_customers_and_casts
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        with pytest.raises(IntegrityError):
            BillCustomerNomination.objects.create(
                bill=d['bill'],
                customer=d['customer1'],
                cast=d['cast1'],
                started_at=timezone.now()
            )
    
    def test_nomination_same_customer_different_cast(self, bill_with_customers_and_casts):
        """同じ顧客、別キャストは OK"""
        d = bill_with_customers_and_casts
        
        nom1 = BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        nom2 = BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast2'],
            started_at=timezone.now()
        )
        
        assert nom1.cast != nom2.cast
        assert BillCustomerNomination.objects.filter(
            bill=d['bill'],
            customer=d['customer1']
        ).count() == 2
    
    def test_nomination_different_customers_same_cast(self, bill_with_customers_and_casts):
        """別顧客、同じキャストは OK"""
        d = bill_with_customers_and_casts
        
        nom1 = BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        nom2 = BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer2'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        assert nom1.customer != nom2.customer
        assert BillCustomerNomination.objects.filter(
            bill=d['bill'],
            cast=d['cast1']
        ).count() == 2
    
    def test_nomination_related_name_from_bill(self, bill_with_customers_and_casts):
        """bill.customer_nominations で逆参照"""
        d = bill_with_customers_and_casts
        
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer2'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        nominations = d['bill'].customer_nominations.all()
        assert nominations.count() == 2
    
    def test_nomination_related_name_from_customer(self, bill_with_customers_and_casts):
        """customer.bill_nominations で逆参照"""
        d = bill_with_customers_and_casts
        
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        nominations = d['customer1'].bill_nominations.all()
        assert nominations.count() == 1
        assert nominations.first().cast == d['cast1']
    
    def test_nomination_related_name_from_cast(self, bill_with_customers_and_casts):
        """cast.customer_nominations で逆参照"""
        d = bill_with_customers_and_casts
        
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer2'],
            cast=d['cast1'],
            started_at=timezone.now()
        )
        
        nominations = d['cast1'].customer_nominations.all()
        assert nominations.count() == 2

@pytest.mark.django_db
class TestBillCustomerReplaceAPI:
    """BillCustomer の customer 差し替え API テスト"""
    
    @pytest.fixture
    def api_setup(self):
        """API テスト用の準備"""
        from rest_framework.test import APIClient
        from accounts.models import User
        
        store = Store.objects.create(name='Test Store', slug='test-store')
        user = User.objects.create_user(username='testuser', password='testpass')
        
        table = Table.objects.create(store=store, code='T01')
        bill = Bill.objects.create(table=table)
        
        # 顧客を3人作成
        customer1 = Customer.objects.create(full_name='Customer 1', phone='+81901234567')
        customer2 = Customer.objects.create(full_name='Customer 2', phone='+81901234568')
        customer3 = Customer.objects.create(full_name='Customer 3', phone='+81901234569')
        
        # BillCustomer を作成（customer1 を参加させる）
        bill_customer = BillCustomer.objects.create(bill=bill, customer=customer1)
        
        client = APIClient()
        client.force_authenticate(user=user)
        client.defaults['HTTP_X_STORE_ID'] = str(store.id)
        
        return {
            'store': store,
            'user': user,
            'bill': bill,
            'customer1': customer1,
            'customer2': customer2,
            'customer3': customer3,
            'bill_customer': bill_customer,
            'client': client,
        }
    
    def test_patch_billcustomer_replace_customer(self, api_setup):
        """PATCH /api/billing/bill-customers/{id}/ で customer を差し替える"""
        d = api_setup
        
        # customer1 → customer2 に差し替え
        url = f'/api/billing/bill-customers/{d["bill_customer"].id}/'
        data = {'customer': d['customer2'].id}
        
        response = d['client'].patch(url, data, format='json')
        assert response.status_code == 200
        
        # DB で確認
        updated = BillCustomer.objects.get(id=d['bill_customer'].id)
        assert updated.customer == d['customer2']
        assert updated.arrived_at is not None  # arrived_at は変わらない
    
    def test_patch_billcustomer_duplicate_customer_reject(self, api_setup):
        """同じ bill に同じ customer が既に存在する場合、差し替えを拒否"""
        d = api_setup
        
        # customer2 を同じ bill に追加
        BillCustomer.objects.create(bill=d['bill'], customer=d['customer2'])
        
        # customer1 → customer2 に差し替えようとする（customer2 は既に参加）
        url = f'/api/billing/bill-customers/{d["bill_customer"].id}/'
        data = {'customer': d['customer2'].id}
        
        response = d['client'].patch(url, data, format='json')
        assert response.status_code == 400
        # unique constraint またはバリデーション エラーが返される
        assert 'customer' in response.data or 'non_field_errors' in response.data
    
    def test_patch_billcustomer_self_replace_allowed(self, api_setup):
        """自分自身の customer を指定する場合は OK（冪等性）"""
        d = api_setup
        
        # customer1 → customer1 に差し替え（自分自身）
        url = f'/api/billing/bill-customers/{d["bill_customer"].id}/'
        data = {'customer': d['customer1'].id}
        
        response = d['client'].patch(url, data, format='json')
        assert response.status_code == 200
        
        # 変わらないはず
        updated = BillCustomer.objects.get(id=d['bill_customer'].id)
        assert updated.customer == d['customer1']
    
    def test_patch_billcustomer_preserve_times(self, api_setup):
        """customer を差し替える際、arrived_at/left_at は保持される"""
        d = api_setup
        
        # 既に IN/OUT がある状態
        arrived = timezone.now()
        left = arrived + timedelta(hours=2)
        d['bill_customer'].arrived_at = arrived
        d['bill_customer'].left_at = left
        d['bill_customer'].save()
        
        # customer を差し替え
        url = f'/api/billing/bill-customers/{d["bill_customer"].id}/'
        data = {'customer': d['customer2'].id}
        
        response = d['client'].patch(url, data, format='json')
        assert response.status_code == 200
        
        # 時刻は保持されるはず
        updated = BillCustomer.objects.get(id=d['bill_customer'].id)
        assert updated.customer == d['customer2']
        assert updated.arrived_at == arrived
        assert updated.left_at == left