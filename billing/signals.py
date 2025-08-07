from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import Store, Staff, Bill, Customer
from billing.utils.customer_log import log_customer_change

User = get_user_model()

# ---------- デフォルト店舗付与 ----------
@receiver(post_save, sender=User)
def set_default_store(sender, instance, created, **kwargs):
    if created and instance.store_id is None:
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
    # ① 新規 Bill：顧客が 0 人なら stub を 1 人だけ作る
    if created and not instance.customers.exists():
        stub = Customer.objects.create()
        instance.customers.add(stub)
        return

    # ② クローズ時：先頭顧客へ snapshot 保存
    if instance.closed_at and instance.customers.exists():
        cust = instance.customers.first()
        # BillItem は item_master(FK) を持つ想定
        cust.last_drink = ', '.join(
            i.item_master.name if i.item_master else i.name   # ← FK があれば master 名、無ければ行の name
            for i in instance.items.all()
        )
        cust.last_cast  = (
            instance.nominated_casts.last() or
            instance.stays.filter(stay_type='in').last() or
            None
        )
        cust.save(update_fields=['last_drink', 'last_cast', 'updated_at'])
