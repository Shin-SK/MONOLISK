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
            cast=d['cast1']
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
            cast=d['cast1']
        )
        
        with pytest.raises(IntegrityError):
            BillCustomerNomination.objects.create(
                bill=d['bill'],
                customer=d['customer1'],
                cast=d['cast1']
            )
    
    def test_nomination_same_customer_different_cast(self, bill_with_customers_and_casts):
        """同じ顧客、別キャストは OK"""
        d = bill_with_customers_and_casts
        
        nom1 = BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1']
        )
        
        nom2 = BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast2']
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
            cast=d['cast1']
        )
        
        nom2 = BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer2'],
            cast=d['cast1']
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
            cast=d['cast1']
        )
        
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer2'],
            cast=d['cast1']
        )
        
        nominations = d['bill'].customer_nominations.all()
        assert nominations.count() == 2
    
    def test_nomination_related_name_from_customer(self, bill_with_customers_and_casts):
        """customer.bill_nominations で逆参照"""
        d = bill_with_customers_and_casts
        
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer1'],
            cast=d['cast1']
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
            cast=d['cast1']
        )
        
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer2'],
            cast=d['cast1']
        )
        
        nominations = d['cast1'].customer_nominations.all()
        assert nominations.count() == 2
