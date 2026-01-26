"""
Phase F3: Timeline + Nominations API 最小テスト
目的：APIの生存確認のみ（テストカバレッジではなく正常系の動作確認）
"""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from billing.models import (
    Bill, BillCustomer, Customer, Cast, Store, Table,
    BillCustomerNomination
)
from accounts.models import StoreMembership

User = get_user_model()


@pytest.mark.django_db
class TestF3TimelineAndNominationsAPI:
    """F3 Timeline + Nominations API 最小テスト"""
    
    @pytest.fixture
    def setup(self):
        """最小セットアップ（既存テスト方式）"""
        # User & Store
        user = User.objects.create_user(username='staff_f3', password='pass')
        store = Store.objects.create(name='Test Store F3', slug='test-store-f3')
        
        # StoreMembership を作成（権限付与）
        StoreMembership.objects.create(user=user, store=store, is_primary=True)
        
        # テーブル・伝票
        table = Table.objects.create(store=store, code='T01')
        bill = Bill.objects.create(table=table)
        
        # 顧客
        customer_a = Customer.objects.create(full_name='Customer A', phone='+81901234567')
        customer_b = Customer.objects.create(full_name='Customer B', phone='+81901234568')
        
        # Bill に顧客参加
        bill_customer_a = BillCustomer.objects.create(bill=bill, customer=customer_a, arrived_at=timezone.now())
        bill_customer_b = BillCustomer.objects.create(bill=bill, customer=customer_b, arrived_at=timezone.now())
        
        # キャスト
        cast_user1 = User.objects.create_user(username='cast_f3_1', password='pass')
        cast_user2 = User.objects.create_user(username='cast_f3_2', password='pass')
        cast1 = Cast.objects.create(user=cast_user1, stage_name='Cast 1', store=store)
        cast2 = Cast.objects.create(user=cast_user2, stage_name='Cast 2', store=store)
        
        return {
            'user': user,
            'store': store,
            'bill': bill,
            'customer_a': customer_a,
            'customer_b': customer_b,
            'bill_customer_a': bill_customer_a,
            'bill_customer_b': bill_customer_b,
            'cast1': cast1,
            'cast2': cast2,
        }
    
    def test_get_bill_customers_returns_200(self, setup):
        """GET /api/billing/bills/{bill_id}/customers/ が 200 を返す"""
        client = APIClient()
        client.force_authenticate(user=setup['user'])
        client.defaults['HTTP_X_STORE_ID'] = str(setup['store'].id)
        
        url = f'/api/billing/bills/{setup["bill"].id}/customers/'
        response = client.get(url)
        assert response.status_code == 200
        
        # 参加している顧客が返されることを確認（ページネーション対応）
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) >= 2
        # レスポンス形式: {'customer': {id, ...}, 'arrived_at', ...}
        customer_ids = [c['customer']['id'] if isinstance(c.get('customer'), dict) else c.get('customer') for c in results]
        assert setup['customer_a'].id in customer_ids
        assert setup['customer_b'].id in customer_ids
    
    def test_patch_bill_customer_updates_arrived_at(self, setup):
        """PATCH /api/billing/bill-customers/{id}/ で arrived_at を更新できる"""
        client = APIClient()
        client.force_authenticate(user=setup['user'])
        client.defaults['HTTP_X_STORE_ID'] = str(setup['store'].id)
        
        # 既存の BillCustomer の arrived_at を更新
        bill_cust = setup['bill_customer_a']
        original_arrived = bill_cust.arrived_at
        
        url = f'/api/billing/bill-customers/{bill_cust.id}/'
        new_time = timezone.now()
        data = {'arrived_at': new_time.isoformat()}
        
        response = client.patch(url, data, format='json')
        assert response.status_code == 200
        
        # DBを再読み込みして確認（時刻が変わったことを確認）
        bill_cust.refresh_from_db()
        assert bill_cust.arrived_at is not None
        assert bill_cust.arrived_at != original_arrived
    
    def test_post_nominations_creates_multi_cast(self, setup):
        """POST /api/billing/bills/{bill_id}/nominations/ で複数キャスト指名を作成できる"""
        client = APIClient()
        client.force_authenticate(user=setup['user'])
        client.defaults['HTTP_X_STORE_ID'] = str(setup['store'].id)
        
        url = f'/api/billing/bills/{setup["bill"].id}/nominations/'
        data = {
            'customer_id': setup['customer_a'].id,
            'cast_ids': [setup['cast1'].id, setup['cast2'].id]
        }
        
        response = client.post(url, data, format='json')
        assert response.status_code == 201
        
        # 2つの指名が作成されたことを確認
        noms = BillCustomerNomination.objects.filter(
            bill=setup['bill'],
            customer=setup['customer_a']
        )
        assert noms.count() == 2
        cast_ids = [n.cast_id for n in noms]
        assert setup['cast1'].id in cast_ids
        assert setup['cast2'].id in cast_ids
    
    def test_delete_nomination(self, setup):
        """DELETE /api/billing/bills/{bill_id}/nominations/{id}/ で削除できる"""
        client = APIClient()
        client.force_authenticate(user=setup['user'])
        client.defaults['HTTP_X_STORE_ID'] = str(setup['store'].id)
        
        # 指名を事前作成
        nom = BillCustomerNomination.objects.create(
            bill=setup['bill'],
            customer=setup['customer_a'],
            cast=setup['cast1']
        )
        
        url = f'/api/billing/bills/{setup["bill"].id}/nominations/{nom.id}/'
        response = client.delete(url)
        assert response.status_code == 204
        
        # 削除されたことを確認
        assert not BillCustomerNomination.objects.filter(id=nom.id).exists()
