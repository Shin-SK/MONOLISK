# billing/services/customer_charge_reconcile.py
"""
顧客滞在時間に基づく SET / 延長の自動起票（冪等 reconcile）。

- BillがOPENのときだけ自動行を更新（CLOSEDは触らない）
- 各 BillCustomer について:
    - AUTO_SET_60: 必ず qty=1
    - AUTO_EXT_30: qty = ceil(max(0, stay_min - 60) / 30)
- 何回実行しても同じ状態になる（冪等）
"""
import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

AUTO_SET_CODE = "AUTO_SET_60"
AUTO_EXT_CODE = "AUTO_EXT_30"


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b


def _minutes_between(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() // 60))


def _get_store(bill):
    """bill から store を解決（table FK → tables M2M の順で探索）"""
    if bill.table_id and hasattr(bill.table, 'store'):
        return bill.table.store
    t = bill.tables.select_related('store').first()
    return t.store if t else None


def _ensure_auto_master(store, code, category_code, name, duration_min, default_price=0):
    """AUTO 用 ItemMaster を get_or_create。カテゴリが存在しなければ None を返す。"""
    from billing.models import ItemMaster, ItemCategory

    category = ItemCategory.objects.filter(code=category_code).first()
    if category is None:
        logger.warning(
            "ItemCategory '%s' not found — skipping auto master '%s' for store %s",
            category_code, code, store.id,
        )
        return None

    master, _ = ItemMaster.objects.get_or_create(
        store=store,
        code=code,
        defaults={
            'name': name,
            'price_regular': default_price,
            'category': category,
            'duration_min': duration_min,
            'exclude_from_payout': True,
        },
    )
    return master


def _sync_auto_item(bill, customer_id, item_master, target_qty):
    """
    自動起票アイテムを同期。変更があれば True を返す。
    target_qty <= 0 なら削除、>0 なら upsert。
    bulk_create / QuerySet.update を使い、BillItem.save() をバイパスして
    recalc は呼び出し元で一括実行する。
    """
    from billing.models import BillItem

    qs = BillItem.objects.filter(
        bill=bill, customer_id=customer_id, item_master=item_master,
    )
    existing = list(qs.order_by('id'))

    # ---- 削除 ----
    if target_qty <= 0:
        if existing:
            qs.delete()
            return True
        return False

    # ---- 新規作成 ----
    if not existing:
        BillItem.objects.bulk_create([BillItem(
            bill=bill,
            customer_id=customer_id,
            item_master=item_master,
            name=item_master.name,
            price=item_master.price_regular,
            qty=target_qty,
            exclude_from_payout=True,
        )])
        return True

    # ---- 既存更新 ----
    changed = False
    first = existing[0]
    if first.qty != target_qty:
        qs.filter(id=first.id).update(qty=target_qty)
        changed = True

    # 重複があれば削除
    if len(existing) > 1:
        extras = [e.id for e in existing[1:]]
        BillItem.objects.filter(id__in=extras).delete()
        changed = True

    return changed


@transaction.atomic
def reconcile_customer_charges(bill_id: int, now=None) -> None:
    """
    伝票内の全 BillCustomer について AUTO_SET / AUTO_EXT を冪等に同期する。
    CLOSED 伝票は何もしない。
    """
    from billing.models import Bill, BillItem, BillCustomer, StoreSeatSetting

    now = now or timezone.now()

    bill = (
        Bill.objects
        .select_for_update()
        .select_related("table__store")
        .get(id=bill_id)
    )

    if bill.closed_at is not None:
        return

    store = _get_store(bill)
    if store is None:
        return

    # デフォルト価格を StoreSeatSetting から取得
    seat_setting = StoreSeatSetting.objects.filter(store=store).first()
    set_price = (seat_setting.charge_per_person or 0) if seat_setting else 0
    ext_price = (seat_setting.extension_30_price or 0) if seat_setting else 0

    auto_set = _ensure_auto_master(
        store, AUTO_SET_CODE, 'set', 'セット（60分）', 60, set_price,
    )
    auto_ext = _ensure_auto_master(
        store, AUTO_EXT_CODE, 'extension', '延長（30分）', 30, ext_price,
    )

    if auto_set is None or auto_ext is None:
        return

    bcs = list(BillCustomer.objects.filter(bill=bill))
    active_customer_ids = set()

    changed = False
    for bc in bcs:
        if not bc.customer_id:
            continue
        active_customer_ids.add(bc.customer_id)

        if not bc.arrived_at:
            # arrived_at 未確定 → 起票しない
            continue

        end_at = bc.left_at or now
        stay_min = _minutes_between(bc.arrived_at, end_at) if end_at > bc.arrived_at else 0

        # SET は必ず 1
        set_qty = 1
        # 延長（30分単位・切り上げ、上限99）
        over = max(0, stay_min - 60)
        ext_qty = min(_ceil_div(over, 30), 99) if over > 0 else 0

        changed |= _sync_auto_item(bill, bc.customer_id, auto_set, set_qty)
        changed |= _sync_auto_item(bill, bc.customer_id, auto_ext, ext_qty)

    # 現在の BillCustomer にいない顧客の自動アイテムを削除（顧客差し替え対応）
    if active_customer_ids:
        orphans = BillItem.objects.filter(
            bill=bill,
            item_master__in=[auto_set, auto_ext],
        ).exclude(customer_id__in=active_customer_ids)
    else:
        orphans = BillItem.objects.filter(
            bill=bill,
            item_master__in=[auto_set, auto_ext],
        )
    if orphans.exists():
        orphans.delete()
        changed = True

    # まとめて一回だけ recalc
    if changed:
        from billing.models import _recalc_bill_after_items_change
        bill.update_expected_out(save=True)
        _recalc_bill_after_items_change(bill)
