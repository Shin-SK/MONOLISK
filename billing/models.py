# billing/models.py  ※TAB インデント
from __future__ import annotations
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.db import models, transaction 
from django.utils import timezone
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField
from django.db.models import Sum 
from django.db.models.signals import post_delete
from django.dispatch import receiver
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
import warnings
from django.db.models import Q

from .calculator import BillCalculator

User = get_user_model()


class BillingUser(User):
    class Meta:
        proxy = True                # DB テーブルはそのまま
        app_label = 'billing'       # ★ここを偽装するとサイドバーの見出しが billing になる
        verbose_name = 'User'
        verbose_name_plural = 'Users'

# ───────── マスター ─────────
class Store(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=50)
    service_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.10'))
    tax_rate     = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.10'))
    nom_pool_rate = models.DecimalField(  # 0.50 = 50 %
        max_digits=4, decimal_places=2, default=Decimal("0.50"),
        verbose_name="本指名率")

    def __str__(self): return self.name


class Table(models.Model):
    store  = models.ForeignKey(Store, on_delete=models.CASCADE)
    number = models.PositiveSmallIntegerField()
    class Meta:
        verbose_name = 'テーブル番号'
        verbose_name_plural = verbose_name
        unique_together = ('store', 'number')
        ordering = ['store', 'number']
    def __str__(self): return f'T{self.number}'


# ── バック率を 3 レーン持つカテゴリ
class ItemCategory(models.Model):
    code  = models.CharField(max_length=20, primary_key=True)      # 'set' 'drink' …
    name  = models.CharField(max_length=30)
    back_rate_free       = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
    back_rate_nomination = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
    back_rate_inhouse    = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
    show_in_menu = models.BooleanField(
        default=False,
        verbose_name='POSメニューに表示'
    )
    def __str__(self): return self.name


class Cast(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='ユーザー'
    )
    stage_name = models.CharField('源氏名', max_length=50)
    hourly_wage = models.PositiveIntegerField('時給', null=True, blank=True)
    store = models.ForeignKey(
        Store, on_delete=models.CASCADE,
        verbose_name='店舗', null=True, blank=True
    )

    # ─ バック率上書き ─────────────────────
    back_rate_free_override = models.DecimalField(
        'バック率（フリー）', max_digits=4, decimal_places=2,
        null=True, blank=True
    )
    back_rate_nomination_override = models.DecimalField(
        'バック率（指名）', max_digits=4, decimal_places=2,
        null=True, blank=True
    )
    back_rate_inhouse_override = models.DecimalField(
        'バック率（場内）', max_digits=4, decimal_places=2,
        null=True, blank=True
    )

    avatar = CloudinaryField(
        'アバター',                # ← 第1引数にラベル
        folder="avatars",
        format="jpg",
        blank=True, null=True
    )

    class Meta:
        verbose_name = 'キャスト'
        verbose_name_plural = verbose_name


# ───────── スタッフ ──────────
class Staff(models.Model):
    """ホール／バーテンダーなど時給制スタッフ"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='ユーザー'
    )
    stores = models.ManyToManyField(          # 将来の“複数店舗兼務”に備えて M2M
        Store,
        verbose_name='所属店舗',
        blank=True,
        related_name='staff_members',
    )
    hourly_wage = models.PositiveIntegerField('時給', default=1300)

    class Meta:
        verbose_name = 'スタッフ'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user.username}（時給¥{self.hourly_wage}）'



class ItemMaster(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name      = models.CharField(max_length=40)
    price_regular = models.PositiveIntegerField()
    price_late    = models.PositiveIntegerField(null=True, blank=True)
    apply_service       = models.BooleanField(default=True)
    exclude_from_payout = models.BooleanField(default=False)
    track_stock         = models.BooleanField(default=False)
    code = models.CharField(max_length=30, blank=True, db_index=True)
    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.PROTECT,
        related_name='items'
    )
    duration_min   = models.PositiveSmallIntegerField(default=0)
    def __str__(self): return self.name


class ItemStock(models.Model):
    item = models.OneToOneField(ItemMaster, on_delete=models.CASCADE, related_name='stock')
    qty  = models.IntegerField(default=0)
    def __str__(self): return f'{self.item.name}: {self.qty}'

# ───────── 伝票 ─────────
class Bill(models.Model):
    table = models.ForeignKey('billing.Table', on_delete=models.CASCADE, null=True, blank=True)
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    expected_out = models.DateTimeField('退店予定', null=True, blank=True)

    main_cast = models.ForeignKey(
        'billing.Cast', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='main_bills',
        verbose_name='本指名'
    )
    nominated_casts = models.ManyToManyField('billing.Cast', blank=True, related_name='nominated_bills')

    subtotal = models.PositiveIntegerField(default=0)
    service_charge = models.PositiveIntegerField(default=0)
    tax = models.PositiveIntegerField(default=0)
    grand_total = models.PositiveIntegerField(default=0)

    total = models.PositiveIntegerField(default=0)          # close 時に確定
    settled_total = models.PositiveIntegerField(null=True, blank=True, default=None)
    discount_rule = models.ForeignKey(
        'billing.DiscountRule',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    
    @property
    def set_rounds(self):
        """SET 行の行数（ラウンド数）"""
        return self.items.filter(item_master__code__startswith='set').count()

    @property
    def ext_minutes(self):
        qs = self.items.filter(
            Q(item_master__code__startswith='extension') |
            Q(item_master__code__startswith='ext')
        )
        return sum(
            (it.duration_min or 30) * it.qty
            for it in qs
        )

    # ─── 金額再計算 ───────────────────────────────
    def recalc(self, save: bool = False):  # noqa: D401
        """DEPRECATED: BillCalculator へ移行中"""
        warnings.warn("Bill.recalc() は BillCalculator に置換予定", DeprecationWarning, stacklevel=2)
        
        sub = sum(it.subtotal for it in self.items.all())
        store = self.table.store if self.table_id else None
        sr = Decimal(store.service_rate) if store else Decimal('0')
        tr = Decimal(store.tax_rate) if store else Decimal('0')
        sr = sr / 100 if sr >= 1 else sr
        tr = tr / 100 if tr >= 1 else tr
        svc = int((Decimal(sub) * sr).quantize(Decimal('1'), ROUND_HALF_UP))
        tax = int((Decimal(sub + svc) * tr).quantize(Decimal('1'), ROUND_HALF_UP))
        self.subtotal = sub
        self.service_charge = svc
        self.tax = tax
        self.grand_total = sub + svc + tax
        if save:
            self.save(update_fields=['subtotal', 'service_charge', 'tax', 'grand_total'])
        return self.grand_total

    # ─── 退店予定再計算 ───────────────────────────
    def update_expected_out(self, save: bool = False):
        minutes = 0
        base_found = False
        for it in self.items.all():
            code = (it.code or '').lower()
            dur = it.duration_min or 0
            if code.startswith('set') and not base_found:
                base_found = True
                minutes += dur
            elif code.startswith(('extension', 'ext')):
                minutes += dur * it.qty
        self.expected_out = self.opened_at + timedelta(minutes=minutes) if minutes else None
        if save:
            self.save(update_fields=['expected_out'])
        return self.expected_out

    
    def close(self, settled_total: int | None = None):
        """伝票を締め、金額・CastPayout・日次サマリを確定保存"""
        result = BillCalculator(self).execute()

        # ─ 金額フィールド更新 ─
        self.subtotal       = result.subtotal
        self.service_charge = result.service_fee
        self.tax            = result.tax
        self.grand_total    = result.total
        self.total          = settled_total or result.total
        if settled_total is not None:
            self.settled_total = settled_total
        self.closed_at = timezone.now()

        from .models import CastPayout, CastDailySummary  # ループ依存対策

        with transaction.atomic():
            # ① 退席前に stay_type をキャッシュ
            stay_map = {
                s.cast_id: s.stay_type
                for s in self.stays.filter(left_at__isnull=True)
            }

            # ② 伝票を確定
            self.save(update_fields=[
                'subtotal', 'service_charge', 'tax', 'grand_total',
                'total', 'settled_total', 'closed_at'
            ])

            # ③ 一括退席
            self.stays.filter(left_at__isnull=True).update(left_at=self.closed_at)

            # ④ CastPayout をリフレッシュ
            self.payouts.all().delete()
            CastPayout.objects.bulk_create(result.cast_payouts)

            # ⑤ cast_id → 売上合計を集計
            sales_map = defaultdict(int)
            for it in self.items.select_related('served_by_cast'):
                if not it.served_by_cast:
                    continue
                sales_map[it.served_by_cast_id] += it.subtotal   # ← “小計” で集計中ならこれ

            work_date = self.closed_at.date()

            # テーブルが無い伝票でも落ちないようにフォールバック
            store_id = (
                self.table.store_id if self.table_id else
                self.store_id       if self.store_id  else
                next(iter(stay_map)) and self.stays.first().bill.table.store_id  # 最後の保険
            )

            # ⑥ CastDailySummary を upsert
            for cid, amt in sales_map.items():
                col = {
                    'nom': 'sales_nom', 'in': 'sales_in', 'free': 'sales_free',
                }.get(stay_map.get(cid, 'free'), 'sales_free')

                rec, _ = CastDailySummary.objects.get_or_create(
                    store_id=store_id, cast_id=cid, work_date=work_date,
                    defaults={}
                )
                setattr(rec, col, (getattr(rec, col) or 0) + amt)
                rec.save(update_fields=[col])

    class Meta:
        verbose_name = '伝票'
        verbose_name_plural = verbose_name



# ───────── 品目行 ─────────
class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    item_master = models.ForeignKey('billing.ItemMaster', null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=40, blank=True)
    price = models.PositiveIntegerField(null=True, blank=True)
    qty = models.PositiveSmallIntegerField(default=1)
    served_by_cast = models.ForeignKey('billing.Cast', null=True, blank=True, on_delete=models.SET_NULL)

    is_nomination = models.BooleanField(default=False, null=True)
    is_inhouse = models.BooleanField(default=False, null=True)
    exclude_from_payout = models.BooleanField(default=False, null=True)

    class Meta:
        ordering = ['id']

    # ---------------- プロパティ -----------------
    @property
    def code(self):
        return self.item_master.code if self.item_master else ''

    @property
    def duration_min(self):
        return self.item_master.duration_min if self.item_master else 0

    @property
    def subtotal(self):
        return (self.price or 0) * (self.qty or 0)

    @property
    def back_rate(self):
        """
        admin.list_display 用。ItemCategory から既定率を引き、キャスト個別上書きを考慮
        """
        if self.served_by_cast is None:
            return Decimal('0.00')

        if not self.item_master:
            return Decimal('0.00')

        try:
            cat = ItemCategory.objects.get(code=self.item_master.category.code)
        except ItemCategory.DoesNotExist:
            return Decimal('0.00')

        if self.is_nomination:
            return (self.served_by_cast.back_rate_nomination_override
                    or cat.back_rate_nomination)
        elif self.is_inhouse:
            return (self.served_by_cast.back_rate_inhouse_override
                    or cat.back_rate_inhouse)
        else:
            return (self.served_by_cast.back_rate_free_override
                    or cat.back_rate_free)

    # --------------- save / delete ---------------
    def save(self, *args, **kwargs):
        self.is_nomination = bool(self.is_nomination)
        self.is_inhouse    = bool(self.is_inhouse)
        if self.item_master:
            self.name = self.name or self.item_master.name
            self.price = self.price or self.item_master.price_regular
            if self.item_master.exclude_from_payout:
                self.exclude_from_payout = True

        super().save(*args, **kwargs)

        # SET / EXTENSION 系なら退店予定を即時更新
        if self.code.startswith(('set', 'extension', 'ext')):
            self.bill.update_expected_out(save=True)

    def delete(self, *args, **kwargs):
        bill = self.bill
        super().delete(*args, **kwargs)
        bill.update_expected_out(save=True)


# ─── 保険：post_delete シグナル（save 内で更新しているので省略可） ─
@receiver(post_delete, sender=BillItem)
def _billitem_deleted_recalc(sender, instance, **kwargs):
    instance.bill.update_expected_out(save=True)



class BillCastStay(models.Model):
    STAY_TYPE = [
        ('free', 'フリー'),      # 付け回し・フリー
        ('in',   '場内指名'),
        ('nom',  '本指名'),
    ]
    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name='stays'
    )
    cast       = models.ForeignKey(Cast, on_delete=models.CASCADE)
    entered_at = models.DateTimeField()
    left_at    = models.DateTimeField(null=True, blank=True)
    stay_type  = models.CharField(
        max_length=4, choices=STAY_TYPE, default='free'
    )
    is_inhouse = models.BooleanField(null=True, blank=True)
    nom_weight = models.DecimalField(  # ← NEW!
        max_digits=4, decimal_places=2,
        null=True, blank=True,
        help_text='この伝票だけの本指名バック用ウェイト。未入力なら1扱い'
    )
 
 
    class Meta:
        ordering = ['entered_at']


# ──────────── 信号 (念のため) ────────────
@receiver(post_delete, sender=BillItem)
def _recalc_expected_out_on_delete(sender, instance, **kwargs):
    instance.bill.update_expected_out(save=True)



class CastPayout(models.Model):
    bill_item = models.ForeignKey(BillItem, null=True, blank=True,
                                  on_delete=models.CASCADE, related_name='payouts')
    bill      = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payouts', null=True)
    cast      = models.ForeignKey(Cast, on_delete=models.CASCADE, related_name='payouts', null=True)
    amount    = models.PositiveIntegerField()
    def __str__(self): return f'{self.cast}: ¥{self.amount}'



class CastCategoryRate(models.Model):
    cast      = models.ForeignKey('billing.Cast', on_delete=models.CASCADE,
                                  related_name='category_rates')
    category  = models.ForeignKey('billing.ItemCategory', on_delete=models.CASCADE)
    rate_free       = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    rate_nomination = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    rate_inhouse    = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('cast', 'category')


def rate_from_cast_category(cast, category, is_nom: bool, is_in: bool) -> Decimal | None:
    """
    CastCategoryRate → Cast 上書き → Category 既定 の順で rate を返す。
    該当なしなら None を返す（呼び出し側で fallback する）
    """
    try:
        cr = cast.category_rates.get(category=category)
        if is_nom and cr.rate_nomination is not None:
            return cr.rate_nomination
        if is_in and cr.rate_inhouse is not None:
            return cr.rate_inhouse
        if (not is_nom and not is_in) and cr.rate_free is not None:
            return cr.rate_free
    except CastCategoryRate.DoesNotExist:
        pass  # fall through to cast‑level override / category default

    # Cast 固有の override
    if is_nom and cast.back_rate_nomination_override is not None:
        return cast.back_rate_nomination_override
    if is_in and cast.back_rate_inhouse_override is not None:
        return cast.back_rate_inhouse_override
    if (not is_nom and not is_in) and cast.back_rate_free_override is not None:
        return cast.back_rate_free_override

    # Category 既定
    if is_nom:
        return category.back_rate_nomination
    if is_in:
        return category.back_rate_inhouse
    return category.back_rate_free


@receiver(post_delete, sender=BillItem)
def _billitem_post_delete(sender, instance: 'BillItem', **kwargs):
    instance.bill.update_expected_out(save=True)



# billing/models.py  （ CastShift ― 修正版全文 ）
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone     # ほかのモデルでも使っている前提
from .models import Store, Cast, Staff


class CastShift(models.Model):
    # ─ 基本 FK ──────────────────────────────
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    cast  = models.ForeignKey(Cast,  on_delete=models.CASCADE)

    # ─ 予定枠 ──────────────────────────────
    plan_start = models.DateTimeField('予定開始', null=True, blank=True)
    plan_end   = models.DateTimeField('予定終了', null=True, blank=True)

    # ─ 打刻実績 ────────────────────────────
    clock_in   = models.DateTimeField('出勤', null=True, blank=True)
    clock_out  = models.DateTimeField('退勤', null=True, blank=True)

    # ─ スナップ & 計算結果 ──────────────────
    hourly_wage_snap = models.PositiveIntegerField('時給スナップ', null=True, blank=True)
    worked_min       = models.PositiveIntegerField('勤務分',       null=True, blank=True, editable=False)
    payroll_amount   = models.PositiveIntegerField('給与額',       null=True, blank=True, editable=False)

    # ─ メタ ───────────────────────────────
    class Meta:
        verbose_name = 'キャストシフト'
        verbose_name_plural = verbose_name
        ordering = ['-plan_start']

    # ─ バリデーション ───────────────────────
    def clean(self):
        # Cast と Shift の store 不一致を禁止
        if self.cast.store and self.cast.store_id != self.store_id:
            raise ValidationError('Cast と Shift の store が一致しません。')

    # ─ 保存時のロジック ─────────────────────
    def save(self, *args, **kwargs):
        # 1) 時給スナップ（未設定なら取得）
        if self.hourly_wage_snap is None:
            self.hourly_wage_snap = (
                self.cast.hourly_wage or
                Staff.objects.filter(
                    stores=self.store, user=self.cast.user
                ).values_list('hourly_wage', flat=True).first() or 0
            )

        # 2) 勤務分数を計算
        if self.clock_in and self.clock_out:
            delta = self.clock_out - self.clock_in
            self.worked_min = int(delta.total_seconds() // 60)
        else:
            self.worked_min = None

        # 3) 給与額を計算
        if self.worked_min and self.hourly_wage_snap:
            self.payroll_amount = int(self.hourly_wage_snap * self.worked_min / 60)
        else:
            self.payroll_amount = None

        super().save(*args, **kwargs)


class CastDailySummary(models.Model):
    """1キャスト x 1日 x 店舗 の給与・売上サマリ"""
    store       = models.ForeignKey(Store, on_delete=models.CASCADE)
    cast        = models.ForeignKey(Cast,  on_delete=models.CASCADE, related_name='daily_summaries')
    work_date   = models.DateField()                     # 2025‑07‑28
    worked_min  = models.PositiveIntegerField(default=0) # 分
    payroll     = models.PositiveIntegerField(default=0) # 時給分
    sales_free  = models.PositiveIntegerField(default=0)
    sales_in    = models.PositiveIntegerField(default=0)
    sales_nom   = models.PositiveIntegerField(default=0)
    sales_champ = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('store', 'cast', 'work_date')
        indexes = [
            models.Index(fields=['work_date']),
            models.Index(fields=['cast', 'work_date']),
        ]
        verbose_name = 'キャスト日次サマリ'
        verbose_name_plural = verbose_name

    # —— 更新用ユーティリティ ——
    @classmethod
    def upsert_from_shift(cls, shift: "CastShift"):
        """退勤時などに呼び出して worked_min / payroll を上書き"""
        if not (shift.clock_in and shift.clock_out):
            return
        rec, _ = cls.objects.get_or_create(
            store = shift.store,
            cast  = shift.cast,
            work_date = shift.clock_in.date(),
            defaults  = dict(),
        )
        rec.worked_min = (
            CastShift.objects
            .filter(cast=shift.cast,
                    store=shift.store,
                    clock_in__date=rec.work_date,
                    clock_out__isnull=False)
            .aggregate(total=models.Sum('worked_min'))['total'] or 0
        )
        rec.payroll = (
            CastShift.objects
            .filter(cast=shift.cast,
                    store=shift.store,
                    clock_in__date=rec.work_date,
                    clock_out__isnull=False)
            .aggregate(total=models.Sum(
                models.F('hourly_wage_snap') * models.F('worked_min') / 60)
            )['total'] or 0
        )
        rec.save(update_fields=['worked_min', 'payroll'])

    @property
    def gross_sales(self):
        """テーブル小計ベースの売上合計"""
        return (
            (self.sales_free  or 0) +
            (self.sales_in    or 0) +
            (self.sales_nom   or 0) +
            (self.sales_champ or 0)
        )


@receiver(post_save, sender=CastShift)
def _update_summary(sender, instance, **kwargs):
    if instance.clock_in and instance.clock_out:
        CastDailySummary.upsert_from_shift(instance)
        
        

class DiscountRule(models.Model):
    """伝票全体に適用される単発割引（併用不可）"""
    name = models.CharField(max_length=40)
    amount_off = models.PositiveIntegerField(null=True, blank=True)  # ¥固定値
    percent_off = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # 0.10 = 10%
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "割引ルール"
        verbose_name_plural = verbose_name

    def __str__(self):
        if self.amount_off:
            return f"{self.name}: -¥{self.amount_off}"
        if self.percent_off:
            return f"{self.name}: -{float(self.percent_off)*100}%"
        return self.name
