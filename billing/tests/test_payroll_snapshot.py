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


class PayrollSnapshotChampagneTestCase(TestCase):
    """給与スナップショット・シャンパン原価基準テスト"""

    def setUp(self):
        # テスト用店舗
        self.store = Store.objects.create(
            name="テスト店舗",
            slug="test-shop",
            service_rate=Decimal("10"),
            tax_rate=Decimal("10"),
        )

        # テーブル
        self.table = Table.objects.create(code="1", store=self.store)

        # カテゴリ作成
        self.cat_champagne = ItemCategory.objects.create(
            code="champagne",
            name="シャンパン",
            major_group="champagne",
            back_rate_free=Decimal("0.20"),
        )
        self.cat_drink = ItemCategory.objects.create(
            code="drink",
            name="ドリンク",
            major_group="drink",
            back_rate_free=Decimal("0.30"),
        )

        # キャスト
        user = User.objects.create_user(username="cast1", password="pass")
        self.cast = Cast.objects.create(user=user, stage_name="キャスト1", store=self.store)

        # 伝票
        self.bill = Bill.objects.create(table=self.table)

    def test_snapshot_champagne_with_cost_no_residual(self):
        """
        シャンパン原価基準：cost がある場合、
        snapshot の payroll_effects と breakdown が一致し、
        residual_from_engine が 0 になることを確認。
        """
        item = ItemMaster.objects.create(
            store=self.store,
            name="アルマンド（再現ケース）",
            price_regular=325000,
            cost=Decimal("10000"),  # 原価 10000
            category=self.cat_champagne,
        )
        bill_item = BillItem.objects.create(
            bill=self.bill,
            item_master=item,
            qty=1,
            price=325000,
            served_by_cast=self.cast,
        )

        # Bill をクローズ
        self.bill.close()

        # スナップショット生成確認
        self.assertIsNotNone(self.bill.payroll_snapshot)
        snapshot = self.bill.payroll_snapshot

        # ─────────────────────────────────────────
        # 1) items_info で payroll_effects.amount を確認
        # ─────────────────────────────────────────
        items = snapshot.get("items", [])
        self.assertEqual(len(items), 1)
        
        item_info = items[0]
        payroll_effects = item_info.get("payroll_effects", [])
        self.assertEqual(len(payroll_effects), 1)
        
        effect = payroll_effects[0]
        expected_amount = int(Decimal("10000") * Decimal("0.20"))  # cost * back_rate = 2000
        self.assertEqual(effect["amount"], expected_amount, 
                        f"payroll_effects.amount should be {expected_amount} (cost * rate)")
        self.assertEqual(effect["basis"]["basis_type"], "cost",
                        "basis_type should be 'cost' for champagne")
        self.assertEqual(effect["basis"]["calculation"], "cost * qty * rate")

        # ─────────────────────────────────────────
        # 2) by_cast.breakdown を確認
        # ─────────────────────────────────────────
        by_cast = snapshot.get("by_cast", [])
        self.assertEqual(len(by_cast), 1)
        
        cast_entry = by_cast[0]
        self.assertEqual(cast_entry["amount"], expected_amount,
                        f"by_cast.amount should match item_back amount")
        
        breakdown = cast_entry.get("breakdown", [])
        
        # item_back を抽出
        item_back_entry = None
        residual_entry = None
        for entry in breakdown:
            if entry["type"] == "item_back":
                item_back_entry = entry
            elif entry["type"] == "adjustment":
                residual_entry = entry
        
        self.assertIsNotNone(item_back_entry, "breakdown に item_back が必須")
        self.assertEqual(item_back_entry["amount"], expected_amount,
                        f"breakdown.item_back.amount should be {expected_amount}")
        
        # detail に basis が記録されていること
        detail = item_back_entry["basis"].get("detail", [])
        self.assertEqual(len(detail), 1)
        self.assertEqual(detail[0]["basis"], "cost",
                        "breakdown.item_back.detail[].basis should be 'cost'")

        # ─────────────────────────────────────────
        # 3) residual が出ないことを確認
        # ─────────────────────────────────────────
        if residual_entry:
            # residual が記録されている場合、amount が 0 であること
            self.assertEqual(residual_entry["amount"], 0,
                           f"residual should be 0 (currently {residual_entry['amount']})")

    def test_snapshot_champagne_without_cost_fallback(self):
        """
        シャンパン原価基準：cost がない場合、
        subtotal にフォールバックして計算されることを確認。
        """
        item = ItemMaster.objects.create(
            store=self.store,
            name="シャンパンNV",
            price_regular=15000,
            cost=None,  # 原価なし
            category=self.cat_champagne,
        )
        bill_item = BillItem.objects.create(
            bill=self.bill,
            item_master=item,
            qty=1,
            price=15000,
            served_by_cast=self.cast,
        )

        # Bill をクローズ
        self.bill.close()
        snapshot = self.bill.payroll_snapshot

        # payroll_effects で subtotal で計算されていること
        items = snapshot.get("items", [])
        item_info = items[0]
        effect = item_info.get("payroll_effects", [0])[0]
        
        expected_amount = int(Decimal("15000") * Decimal("0.20"))  # subtotal * rate = 3000
        self.assertEqual(effect["amount"], expected_amount,
                        f"should fallback to subtotal * rate = {expected_amount}")
        self.assertEqual(effect["basis"]["basis_type"], "subtotal",
                        "basis_type should be 'subtotal' when cost is None")

    def test_snapshot_normal_drink_subtotal_basis(self):
        """
        通常ドリンク：cost があってもずっと subtotal で計算されることを確認。
        """
        item = ItemMaster.objects.create(
            store=self.store,
            name="ビール",
            price_regular=1000,
            cost=Decimal("300"),  # cost があるが無視される
            category=self.cat_drink,
        )
        bill_item = BillItem.objects.create(
            bill=self.bill,
            item_master=item,
            qty=2,
            price=1000,
            served_by_cast=self.cast,
        )

        # Bill をクローズ
        self.bill.close()
        snapshot = self.bill.payroll_snapshot

        # payroll_effects で subtotal で計算されていること
        items = snapshot.get("items", [])
        item_info = items[0]
        effect = item_info.get("payroll_effects", [0])[0]
        
        expected_amount = int(Decimal("2000") * Decimal("0.30"))  # subtotal (2000) * rate = 600
        self.assertEqual(effect["amount"], expected_amount,
                        f"should use subtotal * rate = {expected_amount}")
        self.assertEqual(effect["basis"]["basis_type"], "subtotal",
                        "basis_type should be 'subtotal' for non-champagne")
