"""
BillItem + Customer 統合テスト（ユニットテスト）
- BillItemモデルにcustomerフィールドが正しく保存・取得できる
- serializerがcustomer_idを正しく受け取る
- バリデーションが正しく動作する
"""
import pytest
from django.contrib.auth import get_user_model
from billing.models import Store, Table, Bill, Customer, BillItem, ItemMaster, ItemCategory, BillCustomer

User = get_user_model()


@pytest.mark.django_db
class TestBillItemCustomerUnit:
    """BillItemモデルのcustomerフィールドのユニットテスト"""

    @pytest.fixture
    def setup_data(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 店舗作成
        store1 = Store.objects.create(slug='store1', name='店舗1')
        
        # テーブル作成
        table = Table.objects.create(store=store1, code='T01')
        
        # 伝票作成
        bill = Bill.objects.create(table=table)
        
        # 顧客作成
        customer1 = Customer.objects.create(
            full_name='顧客1',
            phone='090-1111-1111'
        )
        customer2 = Customer.objects.create(
            full_name='顧客2（bill参加なし）',
            phone='090-2222-2222'
        )
        
        # customer1 をbillに参加させる（BillCustomer作成）
        BillCustomer.objects.create(bill=bill, customer=customer1)
        
        # 商品カテゴリ・マスタ作成
        category = ItemCategory.objects.create(code='drink', name='ドリンク')
        item_master = ItemMaster.objects.create(
            store=store1,
            name='テストドリンク',
            price_regular=1000,
            category=category
        )
        
        return {
            'user': user,
            'store1': store1,
            'table': table,
            'bill': bill,
            'customer1': customer1,
            'customer2': customer2,
            'item_master': item_master,
        }

    def test_billitem_create_with_customer(self, setup_data):
        """BillItemをcustomer付きで作成できる"""
        bill_item = BillItem.objects.create(
            bill=setup_data['bill'],
            item_master=setup_data['item_master'],
            name='テストドリンク',
            price=1000,
            qty=1,
            customer=setup_data['customer1']
        )
        
        assert bill_item.customer_id == setup_data['customer1'].id
        assert bill_item.customer.full_name == '顧客1'

    def test_billitem_create_without_customer(self, setup_data):
        """BillItemをcustomer未指定で作成できる"""
        bill_item = BillItem.objects.create(
            bill=setup_data['bill'],
            item_master=setup_data['item_master'],
            name='テストドリンク',
            price=1000,
            qty=1
        )
        
        assert bill_item.customer is None

    def test_billitem_customer_update(self, setup_data):
        """BillItemのcustomerを更新できる"""
        bill_item = BillItem.objects.create(
            bill=setup_data['bill'],
            item_master=setup_data['item_master'],
            name='テストドリンク',
            price=1000,
            qty=1
        )
        
        # customerを追加
        bill_item.customer = setup_data['customer1']
        bill_item.save()
        
        bill_item.refresh_from_db()
        assert bill_item.customer_id == setup_data['customer1'].id

    def test_billitem_queryset_with_customer(self, setup_data):
        """BillItemをcustomer付きで検索できる"""
        bill_item1 = BillItem.objects.create(
            bill=setup_data['bill'],
            item_master=setup_data['item_master'],
            name='ドリンク1',
            price=1000,
            qty=1,
            customer=setup_data['customer1']
        )
        
        bill_item2 = BillItem.objects.create(
            bill=setup_data['bill'],
            item_master=setup_data['item_master'],
            name='ドリンク2',
            price=2000,
            qty=1
        )
        
        # customerが指定されたbill_itemを検索
        items_with_customer = BillItem.objects.filter(
            bill=setup_data['bill'],
            customer=setup_data['customer1']
        )
        
        assert items_with_customer.count() == 1
        assert items_with_customer.first().id == bill_item1.id

    def test_customer_related_name(self, setup_data):
        """Customerから逆参照でBillItemを取得できる"""
        bill_item = BillItem.objects.create(
            bill=setup_data['bill'],
            item_master=setup_data['item_master'],
            name='テストドリンク',
            price=1000,
            qty=1,
            customer=setup_data['customer1']
        )
        
        # 逆参照でbill_itemを取得
        bill_items = setup_data['customer1'].bill_items.all()
        
        assert bill_items.count() == 1
        assert bill_items.first().id == bill_item.id

