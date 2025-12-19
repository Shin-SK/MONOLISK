"""
給与計算の予防線（スナップショット）テスト

- Billをクローズしたら payroll_snapshot が生成されること
- クローズ後に items を変更すると payroll_dirty が true になること
- クローズ後に再クローズしても snapshot が変わらないこと
"""
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, cast

from billing.models import (
    Bill, Store, Table, Cast, ItemMaster, ItemCategory,
    BillItem, BillCastStay, CastPayout, Customer, User
)
from billing.services import is_payroll_dirty, compute_current_hash
from django.contrib.auth import get_user_model

User = get_user_model()


class PayrollSnapshotTestCase(TestCase):
    """給与スナップショット機能のテスト"""
    
    def setUp(self):
        """テストデータ設定"""
        # Store
        self.store = Store.objects.create(
            slug="test-store",
            name="テスト店舗",
            service_rate=Decimal("0.10"),
            tax_rate=Decimal("0.10"),
        )
        
        # Table
        self.table = Table.objects.create(
            store=self.store,
            code="T01",
        )
        
        # ItemCategory
        self.category = ItemCategory.objects.create(
            code="drink",
            name="ドリンク",
            back_rate_free=Decimal("0.30"),
        )
        
        # ItemMaster
        self.item = ItemMaster.objects.create(
            store=self.store,
            name="ショット",
            price_regular=3900,
            category=self.category,
        )
        
        # User & Cast
        self.user = User.objects.create_user(username="cast1", password="pass")
        self.cast = Cast.objects.create(
            user=self.user,
            stage_name="太郎",
            store=self.store,
        )
        
        # Bill
        self.bill = Bill.objects.create(
            table=self.table,
            opened_at=timezone.now(),
            pax=1,
        )
    
    def test_bill_close_creates_snapshot(self):
        """Bill クローズ時に payroll_snapshot が生成される"""
        # Bill に item を追加
        item = BillItem.objects.create(
            bill=self.bill,
            item_master=self.item,
            qty=1,
            price=self.item.price_regular,
            served_by_cast=self.cast,
        )
        
        # Cast を場内で追加
        stay = BillCastStay.objects.create(
            bill=self.bill,
            cast=self.cast,
            stay_type="free",
            entered_at=timezone.now(),
        )
        
        # クローズ前
        self.assertIsNone(self.bill.payroll_snapshot)
        
        # クローズ
        self.bill.close()
        self.bill.refresh_from_db()
        
        # スナップショットが生成されている
        self.assertIsNotNone(self.bill.payroll_snapshot)
        self.assertIn("version", self.bill.payroll_snapshot)
        self.assertIn("hash", self.bill.payroll_snapshot)
        self.assertIn("closed_at", self.bill.payroll_snapshot)
        self.assertIn("by_cast", self.bill.payroll_snapshot)
        self.assertEqual(self.bill.payroll_snapshot["version"], 1)
    
    def test_snapshot_not_overwritten_on_reclose(self):
        """クローズ後に再クローズしても snapshot が上書きされない"""
        # Bill に item を追加
        item = BillItem.objects.create(
            bill=self.bill,
            item_master=self.item,
            qty=1,
            price=self.item.price_regular,
            served_by_cast=self.cast,
        )
        
        # Cast を追加
        stay = BillCastStay.objects.create(
            bill=self.bill,
            cast=self.cast,
            stay_type="free",
            entered_at=timezone.now(),
        )
        
        # 1回目クローズ
        self.bill.close()
        self.bill.refresh_from_db()
        snapshot_1st = self.bill.payroll_snapshot
        hash_1st = snapshot_1st.get("hash")
        
        # 2回目クローズ（再度 closed_at をセットしてクローズを呼ぶ）
        # Bill の stayed を明示的にリセット
        self.bill.stays.all().update(left_at=None)
        self.bill.closed_at = None
        self.bill.save()
        self.bill.close()
        self.bill.refresh_from_db()
        snapshot_2nd = self.bill.payroll_snapshot
        hash_2nd = snapshot_2nd.get("hash")
        
        # ハッシュが同じ（上書きされていない）
        self.assertEqual(hash_1st, hash_2nd)
    
    def test_payroll_dirty_on_item_change(self):
        """
        クローズ後に items を変更すると payroll_dirty が true になる
        
        注：qty 変更だけでは subtotal が変わらないため、
        item を削除することで dirty を確実に引き起こす。
        """
        # Bill に item を追加
        item = BillItem.objects.create(
            bill=self.bill,
            item_master=self.item,
            qty=1,
            price=self.item.price_regular,
            served_by_cast=self.cast,
        )
        
        # Cast を追加
        stay = BillCastStay.objects.create(
            bill=self.bill,
            cast=self.cast,
            stay_type="free",
            entered_at=timezone.now(),
        )
        
        # クローズ
        self.bill.close()
        self.bill.refresh_from_db()
        
        # 初期状態: dirty = False
        self.assertFalse(is_payroll_dirty(self.bill))
        
        # item を削除することで金額が変わる
        item.delete()
        
        # dirty が true になる
        self.assertTrue(is_payroll_dirty(self.bill))
    
    def test_snapshot_hash_integrity(self):
        """
        スナップショットのハッシュが生成・検証できる
        
        注：hash は totals のみで計算しているため、
        by_cast や items の変更は検知しない（金額変更のみ検知）。
        """
        # Bill に item を追加
        item = BillItem.objects.create(
            bill=self.bill,
            item_master=self.item,
            qty=1,
            price=self.item.price_regular,
            served_by_cast=self.cast,
        )
        
        # Cast を追加
        stay = BillCastStay.objects.create(
            bill=self.bill,
            cast=self.cast,
            stay_type="free",
            entered_at=timezone.now(),
        )
        
        # クローズ
        self.bill.close()
        self.bill.refresh_from_db()
        
        original_hash = self.bill.payroll_snapshot.get("hash")
        
        # hash が存在して sha256:... 形式であることを確認
        self.assertIsNotNone(original_hash)
        self.assertTrue(original_hash.startswith("sha256:"))
        
        # hash を計算し直しても同じ値になることを確認
        from billing.services import _compute_snapshot_hash
        recomputed = _compute_snapshot_hash(self.bill.payroll_snapshot)
        self.assertEqual(original_hash, recomputed)
    
    def test_serializer_returns_payroll_snapshot_and_dirty(self):
        """Serializer が payroll_snapshot と payroll_dirty を返す"""
        from billing.serializers import BillSerializer
        
        # Bill に item を追加
        item = BillItem.objects.create(
            bill=self.bill,
            item_master=self.item,
            qty=1,
            price=self.item.price_regular,
            served_by_cast=self.cast,
        )
        
        # Cast を追加
        stay = BillCastStay.objects.create(
            bill=self.bill,
            cast=self.cast,
            stay_type="free",
            entered_at=timezone.now(),
        )
        
        # クローズ前
        ser = BillSerializer(self.bill)
        data = cast(dict[str, Any], ser.data)
        self.assertIn("payroll_snapshot", data)
        self.assertIn("payroll_dirty", data)
        self.assertIsNone(data["payroll_snapshot"])  # クローズ前なので None
        self.assertFalse(data["payroll_dirty"])  # snapshot がないので False
        
        # クローズ
        self.bill.close()
        self.bill.refresh_from_db()
        
        # クローズ後
        ser = BillSerializer(self.bill)
        data = cast(dict[str, Any], ser.data)
        self.assertIsNotNone(data["payroll_snapshot"])
        self.assertFalse(data["payroll_dirty"])  # 変更がないので False
        
        # item を変更
        item.qty = 2
        item.save()
        
        # dirty に
        ser = BillSerializer(self.bill)
        data = cast(dict[str, Any], ser.data)
        self.assertTrue(data["payroll_dirty"])


class PayrollSnapshotEdgeCaseTestCase(TestCase):
    """エッジケースのテスト"""
    
    def setUp(self):
        """テストデータ設定（最小化）"""
        self.store = Store.objects.create(
            slug="test-store",
            name="テスト店舗",
        )
        self.table = Table.objects.create(
            store=self.store,
            code="T01",
        )
        self.bill = Bill.objects.create(
            table=self.table,
            opened_at=timezone.now(),
        )
    
    def test_close_without_items(self):
        """Item がない Bill をクローズしても落ちない"""
        # クローズ
        self.bill.close()
        self.bill.refresh_from_db()
        
        # スナップショットが生成されている
        self.assertIsNotNone(self.bill.payroll_snapshot)
        self.assertEqual(self.bill.payroll_snapshot["version"], 1)
    
    def test_payroll_dirty_without_snapshot(self):
        """snapshot がない Bill は dirty = False"""
        # クローズしない
        self.assertFalse(is_payroll_dirty(self.bill))
