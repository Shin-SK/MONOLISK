"""
Tests for nomination summary (Phase 3)
"""
import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from billing.models import Bill, BillCustomer, BillCustomerNomination, Store, Customer, Cast, Table, BillItem, ItemMaster, ItemCategory
from billing.services.nomination_summary import build_nomination_summaries
from accounts.models import User


@pytest.mark.django_db
class TestNominationSummaryService:
    """本指名期間卓小計計算のユニットテスト"""
    
    @pytest.fixture
    def setup_with_items(self):
        """テスト用のセットアップ（複数BillItemを含む）"""
        # 店舗
        store = Store.objects.create(name='Test Store', slug='test-store')
        
        # テーブル・伝票
        table = Table.objects.create(store=store, code='T01')
        bill = Bill.objects.create(table=table)
        
        # 顧客A、B
        customer_a = Customer.objects.create(full_name='Customer A', phone='+81901234567')
        customer_b = Customer.objects.create(full_name='Customer B', phone='+81901234568')
        
        # Bill参加
        bill_customer_a = BillCustomer.objects.create(bill=bill, customer=customer_a)
        bill_customer_b = BillCustomer.objects.create(bill=bill, customer=customer_b)
        
        # キャスト（複数）
        cast_user1 = User.objects.create_user(username='cast1', password='pass')
        cast_user2 = User.objects.create_user(username='cast2', password='pass')
        cast1 = Cast.objects.create(user=cast_user1, stage_name='Cast 1', store=store)
        cast2 = Cast.objects.create(user=cast_user2, stage_name='Cast 2', store=store)
        
        # アイテムカテゴリ
        category = ItemCategory.objects.create(
            code='drink',
            name='ドリンク',
            major_group='drink'
        )
        
        # アイテムマスター
        item = ItemMaster.objects.create(
            store=store,
            name='テストドリンク',
            price_regular=5000,
            category=category
        )
        
        # 時刻帯を明示（20:30 ~ 21:30 の間に滞在）
        arrived_at = timezone.now().replace(hour=20, minute=30, second=0, microsecond=0)
        left_at = arrived_at + timedelta(hours=1)
        
        bill_customer_a.arrived_at = arrived_at
        bill_customer_a.left_at = left_at
        bill_customer_a.save()
        
        return {
            'bill': bill,
            'customer_a': customer_a,
            'customer_b': customer_b,
            'bill_customer_a': bill_customer_a,
            'cast1': cast1,
            'cast2': cast2,
            'item': item,
            'arrived_at': arrived_at,
            'left_at': left_at,
            'store': store,
        }
    
    def test_single_nomination_subtotal_calculation(self, setup_with_items):
        """（テスト1）単一本指名：区間卓小計が正しく算出される"""
        d = setup_with_items
        
        # 本指名Aを作成：Cast1だけ
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer_a'],
            cast=d['cast1'],
            started_at=d['arrived_at']
        )
        
        # BillItemを3個作成：区間内2個、区間外1個
        # 20:20（区間外） -> ordered_at < arrived_at
        BillItem.objects.create(
            bill=d['bill'],
            item_master=d['item'],
            name='Before arrival',
            price=5000,
            qty=1,
            ordered_at=d['arrived_at'] - timedelta(minutes=10)
        )
        
        # 20:50（区間内） -> arrived_at <= ordered_at < left_at
        BillItem.objects.create(
            bill=d['bill'],
            item_master=d['item'],
            name='During stay 1',
            price=5000,
            qty=2,
            ordered_at=d['arrived_at'] + timedelta(minutes=20)
        )
        
        # 21:20（区間内）
        BillItem.objects.create(
            bill=d['bill'],
            item_master=d['item'],
            name='During stay 2',
            price=5000,
            qty=3,
            ordered_at=d['arrived_at'] + timedelta(minutes=50)
        )
        
        # 21:40（区間外） -> ordered_at >= left_at
        BillItem.objects.create(
            bill=d['bill'],
            item_master=d['item'],
            name='After departure',
            price=5000,
            qty=1,
            ordered_at=d['left_at'] + timedelta(minutes=10)
        )
        
        # 集計実行
        results = build_nomination_summaries(d['bill'])
        
        assert len(results) == 1
        result = results[0]
        
        # 期待値：区間内は 2個×5000 + 3個×5000 = 25000
        assert result['customer_id'] == d['customer_a'].id
        assert result['num_casts'] == 1
        assert result['subtotal'] == '25000'  # 文字列で返される
        assert result['per_cast_share'] == '25000.00'  # 1人で折半、quantizeで小数第2位
    
    def test_multiple_nominations_split(self, setup_with_items):
        """（テスト2）複数本指名：区間卓小計が人数で割られる"""
        d = setup_with_items
        
        # 本指名Aを作成：Cast1 と Cast2（2人）
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer_a'],
            cast=d['cast1'],
            started_at=d['arrived_at']
        )
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer_a'],
            cast=d['cast2'],
            started_at=d['arrived_at']
        )
        
        # BillItemを作成：区間内40000
        BillItem.objects.create(
            bill=d['bill'],
            item_master=d['item'],
            name='During stay',
            price=5000,
            qty=8,
            ordered_at=d['arrived_at'] + timedelta(minutes=20)
        )
        
        results = build_nomination_summaries(d['bill'])
        
        assert len(results) == 1
        result = results[0]
        
        # 期待値：40000 / 2 = 20000
        assert result['subtotal'] == '40000'
        assert result['num_casts'] == 2
        assert result['per_cast_share'] == '20000.00'
    
    def test_left_at_none_uses_now(self, setup_with_items):
        """（テスト3）left_at=None：now をend扱いにして区間が切れる"""
        d = setup_with_items
        
        # Bill Aの left_at を None にセット（退店していない状態）
        d['bill_customer_a'].left_at = None
        d['bill_customer_a'].save()
        
        # 本指名を作成
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=d['customer_a'],
            cast=d['cast1'],
            started_at=d['arrived_at']
        )
        
        # BillItem作成
        now = d['arrived_at'] + timedelta(minutes=30)  # arrived_at + 30分を now とする
        
        # arrived_at + 10分：区間内
        BillItem.objects.create(
            bill=d['bill'],
            item_master=d['item'],
            name='During stay',
            price=5000,
            qty=2,
            ordered_at=d['arrived_at'] + timedelta(minutes=10)
        )
        
        # now + 10分：区間外（未来）
        BillItem.objects.create(
            bill=d['bill'],
            item_master=d['item'],
            name='After now',
            price=5000,
            qty=1,
            ordered_at=now + timedelta(minutes=10)
        )
        
        # now を指定して集計
        results = build_nomination_summaries(d['bill'], now=now)
        
        assert len(results) == 1
        result = results[0]
        
        # 期待値：区間内は 2個×5000 = 10000
        assert result['subtotal'] == '10000'
        assert result['period_status'] == 'ongoing'
    
    def test_arrived_at_none_skipped(self, setup_with_items):
        """（テスト4）arrived_at=None：対象外"""
        d = setup_with_items
        
        # Bill Bを作成：arrived_at = None
        customer_b = d['customer_b']
        bill_customer_b = BillCustomer.objects.get(bill=d['bill'], customer=customer_b)
        bill_customer_b.arrived_at = None
        bill_customer_b.left_at = timezone.now()
        bill_customer_b.save()
        
        # 本指名Bを作成
        BillCustomerNomination.objects.create(
            bill=d['bill'],
            customer=customer_b,
            cast=d['cast1'],
            started_at=d['arrived_at']
        )
        
        results = build_nomination_summaries(d['bill'])
        
        # 結果は空（Aだけが本指名でないため）
        assert len(results) == 0
    
    def test_no_nomination_returns_empty(self, setup_with_items):
        """（テスト5）nominationが無い：resultsが空"""
        d = setup_with_items
        
        # 本指名を作成しない
        results = build_nomination_summaries(d['bill'])
        
        assert len(results) == 0
        assert results == []
    
    def test_decimal_rounding(self, setup_with_items):
        """（テスト6）Decimal丸め：3人割りで端数が出る場合"""
        d = setup_with_items
        
        # 本指名Aを作成：3人
        cast_user3 = User.objects.create_user(username='cast3', password='pass')
        cast3 = Cast.objects.create(user=cast_user3, stage_name='Cast 3', store=d['store'])
        
        BillCustomerNomination.objects.create(bill=d['bill'], customer=d['customer_a'], cast=d['cast1'], started_at=d['arrived_at'])
        BillCustomerNomination.objects.create(bill=d['bill'], customer=d['customer_a'], cast=d['cast2'], started_at=d['arrived_at'])
        BillCustomerNomination.objects.create(bill=d['bill'], customer=d['customer_a'], cast=cast3, started_at=d['arrived_at'])
        
        # BillItem：10000（3で割ると 3333.333...）
        BillItem.objects.create(
            bill=d['bill'],
            item_master=d['item'],
            name='Test',
            price=5000,
            qty=2,
            ordered_at=d['arrived_at'] + timedelta(minutes=20)
        )
        
        results = build_nomination_summaries(d['bill'])
        
        assert len(results) == 1
        result = results[0]
        
        # 丸め: 10000 / 3 = 3333.33 (ROUND_HALF_UP で小数第2位)
        assert result['subtotal'] == '10000'
        assert result['num_casts'] == 3
        # 3333.33... は ROUND_HALF_UP で 3333.33
        assert result['per_cast_share'] == '3333.33'


@pytest.mark.django_db
class TestNominationSummaryAPI:
    """APIエンドポイントのテスト"""
    
    @pytest.fixture
    def api_setup(self):
        """APIテスト用セットアップ"""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        # ユーザー
        user = User.objects.create_user(username='testuser', password='pass')
        
        # 店舗
        store = Store.objects.create(name='Test Store', slug='test-store')
        user.store = store
        user.save()
        
        # テーブル・伝票
        table = Table.objects.create(store=store, code='T01')
        bill = Bill.objects.create(table=table)
        
        return {
            'client': client,
            'user': user,
            'store': store,
            'bill': bill,
        }
    
    def test_api_endpoint_get(self, api_setup):
        """GET /api/billing/bills/{bill_id}/nomination-summaries/ が動作する"""
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token
        
        d = api_setup
        token = Token.objects.create(user=d['user'])
        
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f'Token {token.key}',
            HTTP_X_STORE_ID=str(d['store'].id)
        )
        
        # エンドポイント呼び出し
        url = f'/api/billing/bills/{d["bill"].id}/nomination-summaries/'
        response = client.get(url)
        
        # 200 OK と JSON レスポンスを確認
        assert response.status_code == 200
        assert 'bill_id' in response.json()
        assert 'results' in response.json()
        assert response.json()['bill_id'] == d['bill'].id
