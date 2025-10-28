# billing/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import (
    Store, Staff, Bill, Customer,
    BillItem, OrderTicket,
    ROUTE_NONE, ROUTE_INHERIT,
)

from django.db.models.signals import pre_delete, post_delete, post_save
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce

from .models import Bill, BillItem, CastDailySummary


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




def _rebuild_cast_daily_summaries(store_id: int, work_date):
    """
    該当 store × 日 の CastDailySummary を Bill / BillItem / CastShift から“生集計”で再構築する。
    - 売上は BillItem から cast × stay_type 別に合算
    - 時給は CastShift.payroll_amount を合算（同日・同店）
    """
    from collections import defaultdict
    if not store_id or not work_date:
        return

    # 1) 当日・当店のクローズ済 Bill が対象（opened_at基準にしたいなら変えてOK）
    bills_qs = Bill.objects.filter(
        table__store_id=store_id,
        closed_at__date=work_date,
    ).prefetch_related('stays', 'items__item_master__category')

    # 2) cast × 区分の金額合算
    sums = defaultdict(lambda: {'free':0, 'in':0, 'nom':0, 'champ':0})
    cast_ids_seen = set()

    for b in bills_qs:
        # 伝票内での最新stayを使って stay_type を決める
        latest_by_cast = {}
        for s in b.stays.all():
            cid = getattr(s.cast, 'id', None)
            if not cid: continue
            if (cid not in latest_by_cast) or (s.entered_at and s.entered_at > latest_by_cast[cid].entered_at):
                latest_by_cast[cid] = s

        for it in b.items.all():
            cid = getattr(getattr(it, 'served_by_cast', None), 'id', None)
            if not cid:
                continue
            cast_ids_seen.add(cid)

            st = latest_by_cast.get(cid).stay_type if cid in latest_by_cast else 'free'
            amt = int((it.price or 0) * (it.qty or 0))

            if st == 'nom':
                sums[cid]['nom']  += amt
            elif st == 'in':
                sums[cid]['in']   += amt
            else:
                sums[cid]['free'] += amt

            cat = getattr(it.item_master, 'category', None)
            if cat and cat.code in ('champagne', 'original-champagne'):
                sums[cid]['champ'] += amt

    # 3) 時給（CastShift → payroll_amount 合算）
    from .models import CastShift
    payroll_by_cast = dict(
        CastShift.objects
        .filter(store_id=store_id, clock_in__date=work_date, clock_out__isnull=False)
        .values('cast_id')
        .annotate(pay=Coalesce(Sum('payroll_amount'), Value(0)))
        .values_list('cast_id', 'pay')
    )

    # 4) 既存の当日分を削除 → 再投入
    CastDailySummary.objects.filter(store_id=store_id, work_date=work_date).delete()

    bulks = []
    for cid in cast_ids_seen.union(payroll_by_cast.keys()):
        agg = sums.get(cid, {'free':0,'in':0,'nom':0,'champ':0})
        bulks.append(CastDailySummary(
            store_id    = store_id,
            cast_id     = cid,
            work_date   = work_date,
            worked_min  = 0,  # 必要なら CastShift から Minutes 合算に変えてOK
            payroll     = int(payroll_by_cast.get(cid, 0)),
            sales_free  = int(agg['free']),
            sales_in    = int(agg['in']),
            sales_nom   = int(agg['nom']),
            sales_champ = int(agg['champ']),
        ))
    if bulks:
        CastDailySummary.objects.bulk_create(bulks)


# ---- Bill 削除: 削除後に当日分を再構築（必須） ----

@receiver(pre_delete, sender=Bill)
def _remember_bill_scope(sender, instance: Bill, **kwargs):
    try:
        instance._store_id_for_rebuild = instance.table.store_id if instance.table_id else None
        # “どの日で集計するか” は closed_at（無ければ opened_at の日付）
        base_dt = instance.closed_at or instance.opened_at or timezone.now()
        instance._work_date_for_rebuild = base_dt.date()
    except Exception:
        instance._store_id_for_rebuild = None
        instance._work_date_for_rebuild = None

@receiver(post_delete, sender=Bill)
def _rebuild_after_bill_delete(sender, instance: Bill, **kwargs):
    store_id = getattr(instance, '_store_id_for_rebuild', None)
    work_date = getattr(instance, '_work_date_for_rebuild', None)
    if store_id and work_date:
        transaction.on_commit(lambda: _rebuild_cast_daily_summaries(store_id, work_date))


# ---- Bill クローズ/再クローズ: その日だけ再構築（推奨） ----

@receiver(post_save, sender=Bill)
def _rebuild_after_bill_close(sender, instance: Bill, created, **kwargs):
    # 新規作成時は何もしない（close時にだけ走らせたい）
    if not instance.closed_at:
        return
    try:
        store_id = instance.table.store_id if instance.table_id else None
        work_date = instance.closed_at.date()
    except Exception:
        store_id = None
        work_date = None
    if store_id and work_date:
        transaction.on_commit(lambda: _rebuild_cast_daily_summaries(store_id, work_date))