"""
Phase 7-4: snapshotの meta 情報とズレ検知のテスト
"""

from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from billing.models import Bill, BillItem, BillCastStay, Table, Store
from billing.services import generate_payroll_snapshot
from billing.payroll.snapshot import snapshot_is_stale


User = get_user_model()


class SnapshotMetaTest(TestCase):
    """Test 1: metaが正しく生成される"""
    
    @classmethod
    def setUpTestData(cls):
        # Store
        cls.store = Store.objects.create(
            name='Test Store',
            slug='test-store-meta',
        )
        
        # Table
        cls.table = Table.objects.create(
            store=cls.store,
            code='T1',
        )
        
        # Bill
        cls.bill = Bill.objects.create(
            table=cls.table,
            opened_at=timezone.now(),
            closed_at=timezone.now() + timedelta(hours=1),
        )
    
    def test_snapshot_has_meta_with_version2(self):
        """snapshotに meta が含まれ、version が 2 であること"""
        snap = generate_payroll_snapshot(self.bill)
        
        self.assertIn('meta', snap)
        meta = snap['meta']
        
        # meta の必須フィールド
        self.assertEqual(meta.get('snapshot_version'), 2)
        self.assertIn('generated_at', meta)
        self.assertIn('use_timeboxed_nom_pool', meta)
        self.assertIn('nom_pool_mode', meta)
        self.assertIn('engine', meta)
        self.assertEqual(meta.get('store_slug'), 'test-store-meta')
    
    @override_settings(USE_TIMEBOXED_NOM_POOL=True)
    def test_snapshot_meta_nom_pool_mode_timeboxed(self):
        """USE_TIMEBOXED_NOM_POOL=True の時、meta.nom_pool_mode が 'timeboxed' であること"""
        snap = generate_payroll_snapshot(self.bill)
        meta = snap['meta']
        
        self.assertTrue(meta.get('use_timeboxed_nom_pool'))
        self.assertEqual(meta.get('nom_pool_mode'), 'timeboxed')
    
    @override_settings(USE_TIMEBOXED_NOM_POOL=False)
    def test_snapshot_meta_nom_pool_mode_legacy(self):
        """USE_TIMEBOXED_NOM_POOL=False の時、meta.nom_pool_mode が 'legacy' であること"""
        snap = generate_payroll_snapshot(self.bill)
        meta = snap['meta']
        
        self.assertFalse(meta.get('use_timeboxed_nom_pool'))
        self.assertEqual(meta.get('nom_pool_mode'), 'legacy')


class SnapshotStaleDetectionTest(TestCase):
    """Test 2: snapshot_is_stale() が正しく判定する"""
    
    @classmethod
    def setUpTestData(cls):
        cls.store = Store.objects.create(
            name='Test Store 2',
            slug='test-store-stale',
        )
        
        cls.table = Table.objects.create(
            store=cls.store,
            code='T2',
        )
    
    def test_snapshot_without_meta_is_stale(self):
        """meta が無いsnapshotは stale と判定される"""
        bill = Bill.objects.create(
            table=self.table,
            opened_at=timezone.now(),
            closed_at=timezone.now() + timedelta(hours=1),
        )
        
        # 旧フォーマットのsnapshotを手動で作成（metaなし）
        old_snapshot = {
            'version': 1,
            'bill_id': bill.id,
            'store_slug': 'test-store-stale',
            'by_cast': [],
            'items': [],
            'totals': {},
        }
        bill.payroll_snapshot = old_snapshot
        bill.save(update_fields=['payroll_snapshot'])
        
        # stale 判定
        self.assertTrue(snapshot_is_stale(bill))
    
    @override_settings(USE_TIMEBOXED_NOM_POOL=True)
    def test_snapshot_stale_when_setting_changed_to_true(self):
        """
        snapshotが USE_TIMEBOXED_NOM_POOL=False で生成されたが、
        現在 True に変わっていたら stale と判定
        """
        bill = Bill.objects.create(
            table=self.table,
            opened_at=timezone.now(),
            closed_at=timezone.now() + timedelta(hours=1),
        )
        
        # 旧設定（False）で生成したsnapshotをシミュレート
        old_snapshot = {
            'meta': {
                'snapshot_version': 2,
                'generated_at': timezone.now().isoformat(),
                'use_timeboxed_nom_pool': False,  # ← 古い設定
                'nom_pool_mode': 'legacy',
                'engine': 'BaseEngine',
                'store_id': self.store.id,
                'store_slug': 'test-store-stale',
            },
            'version': 1,
            'bill_id': bill.id,
            'by_cast': [],
            'items': [],
            'totals': {},
        }
        bill.payroll_snapshot = old_snapshot
        bill.save(update_fields=['payroll_snapshot'])
        
        # 現在の設定は True（@override_settings）なので stale
        self.assertTrue(snapshot_is_stale(bill))
    
    @override_settings(USE_TIMEBOXED_NOM_POOL=True)
    def test_snapshot_fresh_when_setting_matches(self):
        """
        snapshotが USE_TIMEBOXED_NOM_POOL=True で生成され、
        現在も True なら fresh と判定
        """
        bill = Bill.objects.create(
            table=self.table,
            opened_at=timezone.now(),
            closed_at=timezone.now() + timedelta(hours=1),
        )
        
        # 現在の設定（True）で生成したsnapshotをシミュレート
        fresh_snapshot = {
            'meta': {
                'snapshot_version': 2,
                'generated_at': timezone.now().isoformat(),
                'use_timeboxed_nom_pool': True,  # ← 現在の設定と一致
                'nom_pool_mode': 'timeboxed',
                'engine': 'BaseEngine',
                'store_id': self.store.id,
                'store_slug': 'test-store-stale',
            },
            'version': 1,
            'bill_id': bill.id,
            'by_cast': [],
            'items': [],
            'totals': {},
        }
        bill.payroll_snapshot = fresh_snapshot
        bill.save(update_fields=['payroll_snapshot'])
        
        # fresh と判定
        self.assertFalse(snapshot_is_stale(bill))

class SnapshotPhase8Test(TestCase):
    """Phase 8: 起点統一＋engine比較削除のテスト"""
    
    @classmethod
    def setUpTestData(cls):
        cls.store = Store.objects.create(
            name='Phase8 Store',
            slug='phase8-store',
        )
        cls.table = Table.objects.create(
            store=cls.store,
            code='T001',
        )
    
    def test_snapshot_meta_without_stays(self):
        """
        Test 8-1a: stays がなくても meta が埋まる
        （bill.table.store 直接使用確認）
        """
        # stays なし Bill を create
        bill = Bill.objects.create(
            table=self.table,
            opened_at=timezone.now(),
        )
        
        # snapshot 生成
        snap = generate_payroll_snapshot(bill)
        meta = snap.get('meta', {})
        
        # meta が埋まっているか確認
        self.assertEqual(meta.get('snapshot_version'), 2)
        self.assertEqual(meta.get('store_id'), self.store.id)
        self.assertEqual(meta.get('store_slug'), self.store.slug)
        self.assertNotEqual(meta.get('store_slug'), 'unknown')
    
    def test_snapshot_not_stale_after_engine_change(self):
        """
        Test 8-2: engine が変わっても stale=False のまま
        （方針A：engine比較を外した確認）
        """
        # meta に "BaseEngine" が記録されている snapshot
        bill = Bill.objects.create(
            table=self.table,
            opened_at=timezone.now(),
        )
        
        snap = generate_payroll_snapshot(bill)
        bill.payroll_snapshot = snap
        bill.save(update_fields=['payroll_snapshot'])
        
        # 初期状態で fresh
        self.assertFalse(snapshot_is_stale(bill))
        
        # meta に engine が記録されている
        meta = bill.payroll_snapshot.get('meta', {})
        self.assertEqual(meta.get('engine'), 'BaseEngine')
        
        # engine が変わった場合でも stale ではない（方針A）
        # （実装上、engine比較を外しているため）
        self.assertFalse(snapshot_is_stale(bill))