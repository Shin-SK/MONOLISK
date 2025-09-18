# billing/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import (
    Store, Staff, Bill, Customer,
    BillItem, OrderTicket,
    ROUTE_NONE, ROUTE_INHERIT,
)

User = get_user_model()

# ---------- デフォルト店舗付与 ----------
@receiver(post_save, sender=User)
def set_default_store(sender, instance, created, **kwargs):
    if created and getattr(instance, "store_id", None) is None:
        default = Store.objects.first()
        if default:
            instance.store = default
            instance.save(update_fields=['store'])

# ---------- Staff 自動作成 ----------
@receiver(post_save, sender=User)
def auto_create_staff(sender, instance, created, **kwargs):
    if instance.is_staff:
        staff, _ = Staff.objects.get_or_create(user=instance)
        if getattr(instance, "store_id", None) and \
           not staff.stores.filter(pk=instance.store_id).exists():
            staff.stores.add(instance.store_id)

# ---------- Bill ↔ Customer 連携（前回情報書き戻し等） ----------
@receiver(post_save, sender=Bill)
def attach_customer_and_snapshot(sender, instance: Bill, created, **kw):
    # ① 新規 Bill：顧客が 0 人なら stub を 1 人作る
    if created and not instance.customers.exists():
        stub = Customer.objects.create()
        instance.customers.add(stub)
        return

    # ② クローズ時：先頭顧客へ snapshot 保存
    if instance.closed_at and instance.customers.exists():
        # last_drink は名前を素直に連結
        cust = instance.customers.first()
        cust.last_drink = ', '.join(
            (i.item_master.name if i.item_master else i.name) or ''
            for i in instance.items.all()
        )

        # Cast を決定（本指名 > 場内 > その他 > main_cast > nominated）
        def pick_cast_for_last():
            stay = (
                instance.stays.filter(stay_type='nom')
                    .select_related('cast').order_by('-entered_at').first()
                or instance.stays.filter(stay_type='in')
                    .select_related('cast').order_by('-entered_at').first()
                or instance.stays.select_related('cast')
                    .order_by('-entered_at').first()
            )
            if stay and stay.cast_id:
                return stay.cast
            if instance.main_cast_id:
                return instance.main_cast
            nom = instance.nominated_casts.order_by('-pk').first()
            return nom or None

        cust.last_cast = pick_cast_for_last()
        cust.save(update_fields=['last_drink', 'last_cast', 'updated_at'])

# ---------- BillItem 作成時：KDSチケット自動発行（1品=1枚） ----------
@receiver(post_save, sender=BillItem)
def create_order_tickets_on_item_create(sender, instance: 'BillItem', created, **kwargs):
    if not created:
        return
    im = getattr(instance, 'item_master', None)
    if not im:
        return

    # 実ルートを決定：アイテムが inherit ならカテゴリの route、なければアイテムの route
    route = im.route
    if route == ROUTE_INHERIT:
        cat = getattr(im, 'category', None)
        route = getattr(cat, 'route', ROUTE_NONE)

    if route == ROUTE_NONE:
        return  # KDS対象外はチケットを作らない

    qty   = int(getattr(instance, 'qty', 1) or 1)
    store = instance.bill.table.store
    by_cast = bool(getattr(instance, 'served_by_cast_id', None))

    OrderTicket.objects.bulk_create([
        OrderTicket(
            bill_item=instance,
            store=store,
            route=route,
            state=OrderTicket.STATE_NEW,
            created_by_cast=by_cast,
        ) for _ in range(qty)
    ])
