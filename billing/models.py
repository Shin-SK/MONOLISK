# billing/models.py
from __future__ import annotations
import warnings
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.db import models, transaction 
from django.utils import timezone
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField
from django.db.models.signals import post_delete
from django.dispatch import receiver
from datetime import timedelta
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import Sum, Q, F, IntegerField, ExpressionWrapper


User = get_user_model()


ROUTE_NONE    = 'none'
ROUTE_KITCHEN = 'kitchen'
ROUTE_DRINKER = 'drinker'
ROUTE_INHERIT = 'inherit'

ROUTE_CHOICES_CATEGORY = [
    (ROUTE_NONE,    'なし'),
    (ROUTE_KITCHEN, 'キッチン'),
    (ROUTE_DRINKER, 'ドリンカー'),
]
ROUTE_CHOICES_ITEM = [
    (ROUTE_INHERIT, 'カテゴリ継承'),
    (ROUTE_NONE,    'なし'),
    (ROUTE_KITCHEN, 'キッチン'),
    (ROUTE_DRINKER, 'ドリンカー'),
]


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

    back_rate_free_default       = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    back_rate_nomination_default = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    back_rate_inhouse_default    = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    back_rate_dohan_default      = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    nom_pool_rate = models.DecimalField(  # 0.50 = 50 %
        max_digits=4, decimal_places=2, default=Decimal("0.50"),
        verbose_name="本指名率")
    business_day_cutoff_hour = models.PositiveSmallIntegerField(
        default=6,
        validators=[MinValueValidator(0), MaxValueValidator(12)],
        help_text="営業日の切替時刻（例: 6 = 朝6時締め。営業日外の処理に使用）",
    )

    # ─────────────── 営業時間 ───────────────────
    business_open_hour = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("20.0"),
        validators=[MinValueValidator(0), MaxValueValidator(27)],
        help_text="営業開始時刻（営業日内の相対時刻。例: 20.0 = 20:00）"
    )
    business_close_hour = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("27.0"),
        validators=[MinValueValidator(0), MaxValueValidator(27)],
        help_text="営業終了時刻（営業日内の相対時刻。例: 27.0 = 朝3:00）"
    )

    @property
    def business_hours_display(self) -> str:
        """営業時間を表示用フォーマット（例: 20:00-27:00）"""
        def hour_to_str(h: Decimal) -> str:
            h_float = float(h)
            h_int = int(h_float)
            m_int = int((h_float - h_int) * 60)
            if h_int >= 24:
                return f"翌{h_int-24:02d}:{m_int:02d}"
            return f"{h_int:02d}:{m_int:02d}"
        
        return f"{hour_to_str(self.business_open_hour)}-{hour_to_str(self.business_close_hour)}"
    
    def is_open_at(self, dt: timezone.datetime = None) -> bool:
        """
        指定時刻（営業日ベース）が営業時間内かチェック
        dt: チェック対象日時（省略時は現在時刻）
        """
        if dt is None:
            dt = timezone.now()
        
        # 営業日時刻に変換（cutoff_hour未満なら前日の時刻扱い）
        hour = Decimal(str(dt.hour + dt.minute / 60.0))
        if dt.hour < self.business_day_cutoff_hour:
            hour += 24  # 朝6時未満なら前日の時刻扱い
        
        return self.business_open_hour <= hour <= self.business_close_hour

    def __str__(self): return self.name


class SeatType(models.Model):
    """席種マスター（Adminで管理）"""
    code = models.CharField(max_length=16, unique=True, db_index=True)
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name = '席種'
        verbose_name_plural = '席種'
        ordering = ['code']

    def __str__(self):
        return self.name


class Table(models.Model):
    store  = models.ForeignKey(Store, on_delete=models.CASCADE)
    code   = models.CharField(
        max_length=16,
        db_index=True,
        null=True, blank=True,
        validators=[RegexValidator(
            regex=r'^[A-Za-z0-9_-]{1,16}$',
            message='英数字・ハイフン・アンダースコアのみ（1〜16文字）。例: T01, B02'
        )],
        help_text='例: T01, B02（英数字可）'
    )
    seat_type = models.ForeignKey(
        SeatType, on_delete=models.PROTECT, db_index=True,
        null=True, blank=True,
        help_text='席種（未設定可）'
    )

    class Meta:
        verbose_name = 'テーブル番号'
        verbose_name_plural = verbose_name
        unique_together = ('store', 'code')
        ordering = ['store', 'code']

    def __str__(self): return self.code


# 席種ごとの店舗設定（席別サービス料率/チャージ/延長等を上書き）
class StoreSeatSetting(models.Model):
    store = models.ForeignKey('billing.Store', on_delete=models.CASCADE, related_name='seat_settings')
    seat_type = models.ForeignKey(SeatType, on_delete=models.CASCADE, db_index=True, null=True, blank=True)

    # 席別の上書き値（未設定は Store 側のデフォルトを使用）
    service_rate = models.DecimalField(  # 0.25 = 25%
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    charge_per_person = models.PositiveIntegerField(null=True, blank=True)
    extension_30_price = models.PositiveIntegerField(null=True, blank=True)
    free_time_price    = models.PositiveIntegerField(null=True, blank=True)
    private_price      = models.PositiveIntegerField(null=True, blank=True)

    memo = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        unique_together = (('store', 'seat_type'),)
        verbose_name = "席種設定"
        verbose_name_plural = "席種設定"

    def __str__(self):
        seat_name = self.seat_type.name if self.seat_type else "未設定"
        return f"{self.store.name} / {seat_name}"



# ── バック率を 3 レーン持つカテゴリ
class ItemCategory(models.Model):
    # 大カテゴリの選択肢（固定7種）
    MAJOR_GROUP_CHOICES = [
        ('drink', 'ドリンク'),
        ('champagne', 'シャンパン'),
        ('food', 'フード'),
        ('other', 'その他商品'),
        ('set', 'セット（人数）'),
        ('extension', '延長'),
        ('other_fee', 'その他料金'),
    ]
    
    code  = models.CharField(max_length=20, primary_key=True)      # 'set' 'drink' …
    name  = models.CharField(max_length=30)
    major_group = models.CharField(
        max_length=20,
        choices=MAJOR_GROUP_CHOICES,
        default='other',
        help_text='集計用の大カテゴリ（7種類で固定）'
    )
    back_rate_free       = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
    back_rate_nomination = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
    back_rate_inhouse    = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
    use_fixed_payout_free_in = models.BooleanField(
        verbose_name='ボトル判定',
        default=False,
        help_text='ボトル判定後はpayroll/engines'
    )
    payout_fixed_per_item = models.PositiveIntegerField(null=True, blank=True)  # ← 復活
    show_in_menu = models.BooleanField(
        default=False,
        verbose_name='POSメニューに表示'
    )
    route = models.CharField(
        max_length=16, choices=ROUTE_CHOICES_CATEGORY,
        default=ROUTE_NONE, db_index=True,
        help_text='このカテゴリのKDS行き先（フード=キッチン、ドリンク=ドリンカー等）'
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
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='ユーザー'
    )
    stores = models.ManyToManyField(
        Store,
        verbose_name='所属店舗',
        blank=True,
        related_name='staff_members',
    )
    hourly_wage = models.PositiveIntegerField('時給', default=1300)
    ROLE_CHOICES = [
        ('staff',  'スタッフ'),
        ('submgr', '副店長'),
        ('mgr',    '店長'),
    ]
    role = models.CharField('役職', max_length=10,
                            choices=ROLE_CHOICES, default='staff')

    class Meta:
        verbose_name = 'スタッフ'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user.username}（時給¥{self.hourly_wage}）'


class StaffShift(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)

    # 予定
    plan_start = models.DateTimeField('予定開始', null=True, blank=True)
    plan_end   = models.DateTimeField('予定終了', null=True, blank=True)

    # 実績
    clock_in  = models.DateTimeField('出勤', null=True, blank=True)
    clock_out = models.DateTimeField('退勤', null=True, blank=True)

    hourly_wage_snap = models.PositiveIntegerField('時給スナップ', null=True, blank=True)
    worked_min       = models.PositiveIntegerField('勤務分',       null=True, blank=True, editable=False)
    payroll_amount   = models.PositiveIntegerField('給与額',       null=True, blank=True, editable=False)

    class Meta:
        verbose_name = 'スタッフシフト'
        verbose_name_plural = verbose_name
        ordering = ['-plan_start']

    # ───── save ロジック ─────
    def save(self, *args, **kwargs):
        # 時給スナップ
        if self.hourly_wage_snap is None:
            self.hourly_wage_snap = self.staff.hourly_wage

        # 勤務時間
        if self.clock_in and self.clock_out:
            delta = self.clock_out - self.clock_in
            self.worked_min = int(delta.total_seconds() // 60)
        else:
            self.worked_min = None

        # 給与
        if self.worked_min and self.hourly_wage_snap:
            self.payroll_amount = int(self.hourly_wage_snap * self.worked_min / 60)
        else:
            self.payroll_amount = None

        super().save(*args, **kwargs)




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

    # 既存フィールド…（省略）
    route = models.CharField(
        max_length=16, choices=ROUTE_CHOICES_ITEM,
        default=ROUTE_INHERIT, db_index=True,
        help_text='KDS行き先。通常は「カテゴリ継承」。必要時のみ個別上書き'
    )

    def __str__(self): return self.name
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['store', 'code'], name='uniq_store_code'),  # ★これ
        ]


class ItemStock(models.Model):
    item = models.OneToOneField(ItemMaster, on_delete=models.CASCADE, related_name='stock')
    qty  = models.IntegerField(default=0)
    def __str__(self): return f'{self.item.name}: {self.qty}'




class CustomerTag(models.Model):
    """顧客属性タグマスター"""
    code = models.SlugField(unique=True, max_length=40, 
                            help_text="内部コード（例: vip / regular / newcomer）")
    name = models.CharField(max_length=50, 
                            help_text="表示名（例: VIP / 常連 / 新規）")
    description = models.TextField(blank=True, 
                                   help_text="説明・使用ガイドライン")
    color = models.CharField(max_length=7, blank=True, default='#808080',
                             help_text="UI表示用カラーコード（例: #FF5733）")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '顧客タグ'
        verbose_name_plural = verbose_name
        ordering = ['code']

    def __str__(self):
        return self.name


class Customer(models.Model):
    full_name  = models.CharField(max_length=100, blank=True)  # 名前
    alias      = models.CharField(max_length=100, blank=True)  # あだ名
    phone      = models.CharField(max_length=30,  blank=True)
    birthday   = models.DateField(null=True, blank=True)
    photo      = models.ImageField(upload_to='cust/', null=True, blank=True)
    memo       = models.TextField(blank=True)
    
    # ★ タグ（複数可）
    tags = models.ManyToManyField(
        'billing.CustomerTag',
        blank=True,
        related_name='customers',
        verbose_name='属性タグ'
    )
    
    # ─────────── マイボトル管理 ───────────────
    has_bottle = models.BooleanField(
        default=False,
        verbose_name='マイボトル有無',
        help_text='マイボトルを預けているか'
    )
    bottle_shelf = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='棚番号',
        help_text='ボトルの保管場所（例: A-12, B-5）'
    )
    bottle_memo = models.TextField(
        blank=True,
        verbose_name='ボトルメモ',
        help_text='銘柄や残量など（例: ジャックダニエル 3/4残）'
    )

    # 自動で書き戻すフィールド
    last_drink = models.CharField(max_length=100, blank=True)
    last_cast  = models.ForeignKey('Cast', null=True, blank=True,
                                   on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def display_name(self):
        return self.alias or self.full_name or f'Guest-{self.id:06d}'


class CustomerLog(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    user     = models.ForeignKey(settings.AUTH_USER_MODEL,
                                 on_delete=models.SET_NULL, null=True)
    action   = models.CharField(max_length=20)      # create / update
    payload  = models.JSONField()                   # 変更後の値
    at       = models.DateTimeField(auto_now_add=True)





# ───────── 伝票 ─────────
class Bill(models.Model):
    table = models.ForeignKey('billing.Table', on_delete=models.CASCADE, null=True, blank=True)
    opened_at = models.DateTimeField(default=timezone.now, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    expected_out = models.DateTimeField('退店予定', null=True, blank=True)
    pax = models.PositiveSmallIntegerField(default=0, verbose_name='人数')
    customers = models.ManyToManyField(
        'billing.Customer',
        through='billing.BillCustomer',
        related_name='bills',
        blank=True,
    )
    main_cast = models.ForeignKey(
        'billing.Cast', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='main_bills',
        verbose_name='本指名'
    )
    nominated_casts = models.ManyToManyField('billing.Cast', blank=True, related_name='nominated_bills')

    memo = models.TextField('メモ', blank=True, default='')
    
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
    paid_cash = models.PositiveIntegerField(default=0)  # 現金受領
    paid_card = models.PositiveIntegerField(default=0)  # カード請求
    
    # ─── 給与計算の予防線（スナップショット） ──────
    payroll_snapshot = models.JSONField(
        null=True, blank=True, 
        verbose_name='給与スナップショット',
        help_text='クローズ時点の給与内訳を保存（不変）'
    )

    @property
    def manual_discount_total(self) -> int:
        return self.manual_discounts.aggregate(s=models.Sum('amount'))['s'] or 0

    @property
    def paid_total(self):
        return (self.paid_cash or 0) + (self.paid_card or 0)

    @property
    def change_due(self):
        st = self.settled_total if self.settled_total is not None else self.grand_total
        st = st or 0
        return max(0, self.paid_total - st)

    @property
    def set_rounds(self):
        """SET 行の行数（ラウンド数）"""
        return self.items.filter(item_master__code__icontains='set').count()

    @property
    def ext_minutes(self):
        qs = self.items.filter(
            Q(item_master__code__icontains='extension') |
            Q(item_master__code__icontains='ext')
        )
        return sum(
            (it.duration_min or 30) * it.qty
            for it in qs
        )

    # ─── 金額再計算 ───────────────────────────────
    def recalc(self, save: bool = False):  # noqa: D401
        from .calculator import BillCalculator
        r = BillCalculator(self).execute()

        self.subtotal       = r.subtotal
        self.service_charge = r.service_fee
        self.tax            = r.tax
        self.grand_total    = r.total

        if save:
            self.save(update_fields=['subtotal','service_charge','tax','grand_total'])
        return self.grand_total

    # ─── 退店予定再計算 ───────────────────────────
    def update_expected_out(self, save: bool = False):
        minutes = 0
        base_found = False
        for it in self.items.all():
            code = (it.code or '').lower()
            dur = it.duration_min or 0
            cat_code = ''
            try:
                cat_code = (getattr(getattr(it, 'item_master', None), 'category', None).code or '').lower()
            except Exception:
                cat_code = ''

            # カテゴリ優先で判定（後方互換でコード接頭辞も許容）
            if (cat_code == 'set' or ('set' in code)) and not base_found:
                base_found = True
                minutes += dur
            elif (cat_code in ('ext', 'extension') or ('extension' in code) or ('ext' in code)):
                minutes += dur * (it.qty or 0)
        self.expected_out = self.opened_at + timedelta(minutes=minutes) if minutes else None
        if save:
            self.save(update_fields=['expected_out'])
        return self.expected_out

    
    def close(self, settled_total: int | None = None):
        from .calculator import BillCalculator
        """伝票を締め、金額・CastPayout・日次サマリを確定保存"""
        # ★ discount_ruleを確実に取得するため、DBから最新状態を取得
        self.refresh_from_db()
        
        result = BillCalculator(self).execute()

        # 閉店時刻は原則「opened_at + SET/EXT 合計分」に合わせる
        # expected_out が未計算の可能性もあるため、ここで最新を計算
        try:
            latest_expected = self.update_expected_out(save=False)
        except Exception:
            latest_expected = None

        # ← ここを追加
        if settled_total is None and self.paid_total:
            settled_total = int(self.paid_total)

        # ─ 金額フィールド更新 ─
        self.subtotal       = result.subtotal
        self.service_charge = result.service_fee
        self.tax            = result.tax
        self.grand_total    = result.total
        self.total          = settled_total or result.total
        if settled_total is not None:
            self.settled_total = settled_total
        # expected_out があればそれを閉店時刻に採用、無ければ現在時刻
        self.closed_at = latest_expected or timezone.now()

        from .models import CastPayout, CastDailySummary  # ループ依存対策
        from billing.services import generate_payroll_snapshot

        with transaction.atomic():
            # ① 給与スナップショット生成（初回クローズのみ。上書きしない）
            if not self.payroll_snapshot:
                self.payroll_snapshot = generate_payroll_snapshot(self)
            
            # ② 退席前に stay_type をキャッシュ
            stay_map = {
                s.cast_id: s.stay_type
                for s in self.stays.filter(left_at__isnull=True)
            }

            # ② 伝票を確定（discount_ruleも保存 + payroll_snapshot）
            self.save(update_fields=[
                'subtotal', 'service_charge', 'tax', 'grand_total',
                'total', 'settled_total', 'closed_at', 'discount_rule', 'payroll_snapshot'
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
            
            # ⑦ 時間別サマリを更新（リアルタイム集計）
            self._update_hourly_summary(store_id, stay_map, sales_map)

    def _update_hourly_summary(self, store_id: int, stay_map: dict, sales_map: dict):
        """時間別サマリ（HourlySalesSummary + HourlyCastSales）を更新"""
        from .models import HourlySalesSummary, HourlyCastSales, ItemCategory
        
        if not self.closed_at:
            return
        
        dt = timezone.localtime(self.closed_at)
        date = dt.date()
        hour = dt.hour
        
        # HourlySalesSummary を取得または作成
        summary, _ = HourlySalesSummary.objects.get_or_create(
            store_id=store_id,
            date=date,
            hour=hour,
            defaults={}
        )
        
        # 全体集計を加算
        summary.sales_total += self.grand_total or 0
        summary.bill_count += 1
        summary.customer_count += self.customers.count()
        
        # カテゴリ別売上を集計
        category_sales = defaultdict(int)
        for item in self.items.select_related('item_master__category'):
            if item.item_master and item.item_master.category:
                cat_code = item.item_master.category.code
                category_sales[cat_code] += item.subtotal
        
        summary.sales_set += category_sales.get('set', 0)
        summary.sales_drink += category_sales.get('drink', 0)
        summary.sales_food += category_sales.get('food', 0)
        summary.sales_champagne += category_sales.get('champagne', 0) + category_sales.get('original-champagne', 0)
        summary.save()
        
        # キャスト別内訳を更新
        for cast_id, total_sales in sales_map.items():
            cast_sales, _ = HourlyCastSales.objects.get_or_create(
                hourly_summary=summary,
                cast_id=cast_id,
                defaults={}
            )
            
            cast_sales.sales_total += total_sales
            cast_sales.bill_count += 1
            
            # stay_type に応じて分類
            stay_type = stay_map.get(cast_id, 'free')
            if stay_type == 'nom':
                cast_sales.sales_nom += total_sales
            elif stay_type == 'in':
                cast_sales.sales_in += total_sales
            else:
                cast_sales.sales_free += total_sales
            
            # シャンパン売上（このキャスト担当分）
            champ_sales = sum(
                item.subtotal for item in self.items.select_related('item_master__category')
                if item.served_by_cast_id == cast_id
                and item.item_master
                and item.item_master.category
                and item.item_master.category.code in ('champagne', 'original-champagne')
            )
            cast_sales.sales_champagne += champ_sales
            cast_sales.save()

    # 席別の実効サービス率（% or 小数両対応）を返すヘルパ
    def _effective_service_rate(self) -> Decimal:
        """
        Table.seat_type に応じて StoreSeatSetting の service_rate を優先。
        未設定なら Store.service_rate を使う。
        """
        # デフォルト
        sr = Decimal('0')
        store = None
        if self.table_id:
            store = self.table.store
        elif hasattr(self, 'store_id') and self.store_id:
            # 伝票が直接 store を持っている場合のフォールバック
            store = Store.objects.filter(id=self.store_id).first()

        if store:
            sr = Decimal(store.service_rate or 0)

            # Table があり seat_type がある場合は上書きを試みる
            if self.table_id and self.table.seat_type:
                s = StoreSeatSetting.objects.filter(
                    store=store, seat_type=self.table.seat_type
                ).only('service_rate').first()
                if s and s.service_rate is not None:
                    sr = Decimal(s.service_rate)

        # 1.00(=100%) と 0.25(=25%) の両方を許容
        return (sr / 100) if sr >= 1 else sr


    class Meta:
        verbose_name = '伝票'
        verbose_name_plural = verbose_name
        constraints = [
            models.CheckConstraint(
                check=models.Q(paid_cash__gte=0) & models.Q(paid_cash__lte=100000000),
                name='bill_paid_cash_range',
            ),
            models.CheckConstraint(
                check=models.Q(paid_card__gte=0) & models.Q(paid_card__lte=100000000),
                name='bill_paid_card_range',
            ),
        ]



def _recalc_bill_after_items_change(bill):
    from .calculator import BillCalculator
    r = BillCalculator(bill).execute()
    bill.subtotal       = r.subtotal
    bill.service_charge = r.service_fee
    bill.tax            = r.tax
    bill.grand_total    = r.total
    bill.save(update_fields=['subtotal','service_charge','tax','grand_total'])



# ───────── 品目行 ─────────
class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    item_master = models.ForeignKey('billing.ItemMaster', null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=40, blank=True)
    price = models.PositiveIntegerField(null=True, blank=True)
    qty = models.PositiveSmallIntegerField(default=1)
    served_by_cast = models.ForeignKey('billing.Cast', null=True, blank=True, on_delete=models.SET_NULL, db_index=True)

    is_nomination = models.BooleanField(default=False, null=True)
    is_inhouse = models.BooleanField(default=False, null=True)
    exclude_from_payout = models.BooleanField(default=False, null=True)
    is_dohan = models.BooleanField(default=False, null=True)  # 同伴料行フラグ（back_rate に 'dohan' を反映）

    back_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    is_nomination = models.BooleanField(default=False)
    is_inhouse    = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                check=models.Q(qty__gte=1) & models.Q(qty__lte=99),
                name='billitem_qty_range',
            ),
            models.CheckConstraint(
                check=models.Q(price__gte=0) & models.Q(price__lte=2000000),
                name='billitem_price_range',
            ),
        ]

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

    def _stay_type_hint(self) -> str:
        if getattr(self, 'is_nomination', False): return 'nom'
        if getattr(self, 'is_inhouse', False):    return 'in'
        if getattr(self, 'is_dohan', False):      return 'dohan'
        return 'free'

    def save(self, *args, **kwargs):
        self.is_nomination = bool(self.is_nomination)
        self.is_inhouse    = bool(self.is_inhouse)
        self.is_dohan      = bool(self.is_dohan)
        if self.item_master:
            self.name  = self.name  or self.item_master.name
            self.price = self.price or self.item_master.price_regular
            if self.item_master.exclude_from_payout:
                self.exclude_from_payout = True

        # back_rate は保存前に解決して持たせる（失敗しても継続）
        # Phase1-1: store 解決を複数経路フォールバック（王道の防波堤）
        try:
            from billing.services.backrate import resolve_back_rate
            import logging
            logger = logging.getLogger(__name__)
            
            bill   = getattr(self, 'bill', None)
            im     = getattr(self, 'item_master', None)
            cat    = getattr(im, 'category', None)
            cast   = getattr(self, 'served_by_cast', None)
            stay   = self._stay_type_hint()
            
            # ★ 優先順位: A. bill.table.store → B. item_master.store → C. bill.store
            store = None
            if bill and hasattr(bill, 'table') and bill.table:
                store = getattr(bill.table, 'store', None)
            
            if not store and im:
                store = getattr(im, 'store', None)
            
            if not store and bill:
                store = getattr(bill, 'store', None)
            
            if store:
                self.back_rate = resolve_back_rate(store=store, category=cat, cast=cast, stay_type=stay)
            else:
                # store が最終的に取得できない場合は警告を出す（back_rate は変更しない）
                logger.warning(
                    f"[BillItem.save] Could not resolve store for back_rate calculation: "
                    f"billitem_id={self.id}, bill_id={self.bill_id}, "
                    f"item_master_id={getattr(im, 'id', 'N/A')}, "
                    f"category_code={getattr(cat, 'code', 'N/A')}, "
                    f"cast_id={getattr(cast, 'id', 'N/A')}, stay_type={stay}. "
                    f"back_rate will remain {self.back_rate} (may default to 0)"
                )
        except Exception as e:
            # import 失敗など根本的な問題を検知できるようにログ出力
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"[BillItem.save] resolve_back_rate failed for item_id={self.id}: {e}. "
                f"back_rate will remain {self.back_rate} (may default to 0)",
                exc_info=True  # スタックトレースも出力
            )

        super().save(*args, **kwargs)

        # SET/EXT なら退店予定更新（カテゴリ優先、後方互換でコード部分一致も）
        cat_id = getattr(getattr(self, 'item_master', None), 'category_id', '') or ''
        code = (self.code or '').lower()
        if (str(cat_id).lower() in ('set', 'ext')) or ('set' in code) or ('extension' in code) or ('ext' in code):
            self.bill.update_expected_out(save=True)

        # ★ ここで金額を再計算（OPEN中でも常に最新に）
        _recalc_bill_after_items_change(self.bill)

    def delete(self, *args, **kwargs):
        bill = self.bill
        super().delete(*args, **kwargs)
        bill.update_expected_out(save=True)
        # ★ 削除時も再計算
        _recalc_bill_after_items_change(bill)





class BillCastStay(models.Model):
    STAY_TYPE = [
        ('free', 'フリー'),      # 付け回し・フリー
        ('in',   '場内指名'),
        ('nom',  '本指名'),
        ('dohan','同伴'),
    ]
    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name='stays'
    )
    cast       = models.ForeignKey(Cast, on_delete=models.CASCADE)
    entered_at = models.DateTimeField()
    left_at    = models.DateTimeField(null=True, blank=True)
    nom_weight = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
        help_text='この伝票だけの本指名バック用ウェイト。未入力なら1扱い'
    )
    stay_type  = models.CharField(max_length=16, choices=STAY_TYPE, db_index=True)  
    is_inhouse = models.BooleanField(null=True, blank=True)
    is_honshimei = models.BooleanField(default=False)  # 本指名トグル（UIでON/OFF）
    is_dohan = models.BooleanField(default=False) #このトグル使うと思う
    is_help       = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['entered_at']

    def clean(self):
        # help は free のときのみ True を許可
        if self.is_help and self.stay_type != 'free':
            raise ValidationError('is_help=True は stay_type="free" の時のみ指定できます。')

    def save(self, *args, **kwargs):
        # stay_type に応じて相互排他フラグを整合
        if self.stay_type == 'dohan':
            self.is_dohan = True
            self.is_honshimei = False
            self.is_help = False                 # help は無効
        elif self.stay_type == 'nom':
            self.is_honshimei = True
            self.is_dohan = False
            self.is_help = False
        elif self.stay_type == 'in':
            self.is_honshimei = False
            self.is_dohan = False
            self.is_help = False                 # 場内時は help 無効
        else:  # 'free'
            self.is_honshimei = False
            self.is_dohan = False
            # is_help はユーザー入力を尊重（clean で整合済み）

        super().save(*args, **kwargs)



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
    business_date = models.DateField(null=True, blank=True, db_index=True)

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

    # ★ 追加: 店舗スコープ
    store = models.ForeignKey(
        'billing.Store',
        on_delete=models.CASCADE,
        related_name='discount_rules',
        null=True, blank=True,   # ← 既存データ移行のため一旦許可（後述）
        db_index=True,
        help_text="この割引ルールを適用できる店舗"
    )

    code = models.SlugField(max_length=40, unique=True, null=True, blank=True,
                            help_text="内部コード（例: initial / agency / referral）")
    name = models.CharField(max_length=40, help_text="表示名（例: 初回 / 案内所 / 顧客紹介）")

    amount_off  = models.PositiveIntegerField(null=True, blank=True)             # ¥固定値
    percent_off = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # 0.10 = 10%

    is_active   = models.BooleanField(default=True)
    is_basic    = models.BooleanField(default=False, db_index=True)

    # ★ 追加: 表示場所フラグ
    show_in_basics = models.BooleanField(default=True, help_text="Basicパネルに表示する")
    show_in_pay    = models.BooleanField(default=True, help_text="会計パネルに表示する")

    # ★ 追加: 並び順（小さいほど上）
    sort_order = models.PositiveSmallIntegerField(default=0)

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "割引ルール"
        verbose_name_plural = verbose_name
        ordering = ['store', 'sort_order', '-created_at']
        constraints = [
            # 店舗+code の組み合わせでユニーク（codeが空のときは除外されることに注意）
            models.UniqueConstraint(
                fields=['store', 'code'],
                name='uniq_store_code_on_discount_rule',
                condition=~models.Q(code__isnull=True) & ~models.Q(code='')
            ),
        ]

    def __str__(self):
        v = (
            f"¥{self.amount_off}"
            if self.amount_off is not None
            else f"{float(self.percent_off)*100:.0f}%"
            if self.percent_off is not None
            else "—"
        )
        s = self.store.name if self.store_id else "GLOBAL"
        return f"[{s}] {self.name} ({self.code or '-'}) -{v}"

    def clean(self):
        # どちらも空はNG／両方指定もNG
        if not self.amount_off and not self.percent_off:
            raise ValidationError("金額引きまたは率引きのどちらかを指定してください。")
        if self.amount_off and self.percent_off:
            raise ValidationError("金額引きと率引きは同時に指定できません。")
        if self.percent_off is not None and self.percent_off < 0:
            raise ValidationError("percent_off は 0 以上で指定してください。")
        



class BillCustomer(models.Model):
    bill      = models.ForeignKey('billing.Bill', on_delete=models.CASCADE)
    customer  = models.ForeignKey('billing.Customer', on_delete=models.PROTECT)
    # 今後用に好きなカラムを足せる（同伴者区分 / ボトル番号 など）
    # joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('bill', 'customer')   # 同じ客を重複登録させない




class StoreNotice(models.Model):
    store = models.ForeignKey('billing.Store', on_delete=models.CASCADE, related_name='notices')

    title = models.CharField(max_length=200)
    body  = models.TextField(blank=True)

    # カバー画像（1枚）
    cover = models.ImageField(upload_to='store_notices/%Y/%m/', blank=True, null=True)

    # 公開制御
    is_published = models.BooleanField(default=False)
    publish_at   = models.DateTimeField(blank=True, null=True)   # 予約公開対応
    pinned       = models.BooleanField(default=False)            # 一覧上部固定

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned', '-publish_at', '-created_at']
        indexes = [
            models.Index(fields=['store', 'is_published', 'publish_at']),
            models.Index(fields=['pinned']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'[{self.store}] {self.title}'

    @property
    def is_visible(self):
        """一般（キャスト側）に見せて良いか"""
        if not self.is_published:
            return False
        if self.publish_at is None:
            return True
        return self.publish_at <= timezone.now()



@receiver(post_delete, sender=BillItem)
def _update_expected_out_on_delete(sender, instance, **kwargs):
    if getattr(instance, "bill_id", None):
        try:
            instance.bill.update_expected_out(save=True)
            _recalc_bill_after_items_change(instance.bill)   # ★ 追加
        except Exception:
            pass


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=BillItem)
def _ensure_expected_out_on_item_save(sender, instance, **kw):
    code = (instance.code or "").lower()
    if code.startswith(("set","extension","ext")):
        instance.bill.update_expected_out(save=True)


class OrderTicket(models.Model):
    STATE_NEW   = 'new'
    STATE_ACK   = 'ack'
    STATE_READY = 'ready'
    STATE_CHOICES = [
        (STATE_NEW,   'NEW'),
        (STATE_ACK,   'ACK'),
        (STATE_READY, 'READY'),
    ]

    bill_item = models.ForeignKey('billing.BillItem', on_delete=models.CASCADE, related_name='tickets')
    store     = models.ForeignKey('billing.Store', on_delete=models.CASCADE, db_index=True)
    route     = models.CharField(max_length=16, db_index=True, default='none')  # kitchen/drinker/none
    state     = models.CharField(max_length=16, choices=STATE_CHOICES, default=STATE_NEW, db_index=True)

    created_by_cast = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    acked_at   = models.DateTimeField(null=True, blank=True)
    ready_at   = models.DateTimeField(null=True, blank=True)
    
    taken_by_staff = models.ForeignKey('billing.Staff', null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name='taken_tickets')
    taken_at       = models.DateTimeField(null=True, blank=True)
    archived_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['store', 'route', 'state', '-created_at']),
            models.Index(fields=['store', 'state', 'archived_at']),
        ]
        ordering = ['created_at']

    def mark_ack(self):
        if self.state == self.STATE_NEW:
            self.state = self.STATE_ACK
            self.acked_at = timezone.now()

    def mark_ready(self):
        if self.state in (self.STATE_NEW, self.STATE_ACK):
            self.state = self.STATE_READY
            self.ready_at = timezone.now()

    def archive_by(self, staff):
        """デシャップで『持ってく』→ 即アーカイブ"""
        self.taken_by_staff = staff
        now = timezone.now()
        self.taken_at = now
        self.archived_at = now


# billing/models.py （末尾あたりに追加）
from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone
try:
    from django.db.models import JSONField  # Django 3.1+
except Exception:
    from django.contrib.postgres.fields import JSONField



class CastGoal(models.Model):
    # 指標
    METRIC_REVENUE       = 'revenue'          # 売上金額（担当分）
    METRIC_NOMINATIONS   = 'nominations'      # 本指名本数
    METRIC_INHOUSE       = 'inhouse'          # 場内指名本数
    METRIC_CHAMP_REVENUE = 'champ_revenue'    # シャンパン売上（通常＋オリジナル）
    METRIC_CHAMP_COUNT   = 'champ_count'      # シャンパン本数（通常＋オリジナル）

    METRIC_CHOICES = [
        (METRIC_REVENUE,       '売上金額'),
        (METRIC_NOMINATIONS,   '本指名本数'),
        (METRIC_INHOUSE,       '場内指名本数'),
        (METRIC_CHAMP_REVENUE, 'シャンパン売上'),
        (METRIC_CHAMP_COUNT,   'シャンパン本数'),
    ]

    # 期間
    PERIOD_DAILY   = 'daily'
    PERIOD_WEEKLY  = 'weekly'
    PERIOD_MONTHLY = 'monthly'
    PERIOD_CUSTOM  = 'custom'
    PERIOD_CHOICES = [
        (PERIOD_DAILY,   '日次'),
        (PERIOD_WEEKLY,  '週次'),
        (PERIOD_MONTHLY, '月次'),
        (PERIOD_CUSTOM,  'カスタム'),
    ]

    cast         = models.ForeignKey('Cast', on_delete=models.CASCADE, related_name='goals')
    metric       = models.CharField(max_length=24, choices=METRIC_CHOICES)
    target_value = models.IntegerField()  # 金額 or 本数
    period_kind  = models.CharField(max_length=16, choices=PERIOD_CHOICES, default=PERIOD_DAILY)
    start_date   = models.DateField(null=True, blank=True)
    end_date     = models.DateField(null=True, blank=True)
    active       = models.BooleanField(default=True)
    # 通知済みマイルストーン（50/80/90/100）を保持して“1回だけ”通知する用
    milestones_hit = JSONField(default=list, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['cast','metric','period_kind','start_date','end_date','active']),
        ]

    MILESTONES = [50, 80, 90, 100]

    def __str__(self):
        return f'Goal({self.cast_id}:{self.metric} {self.target_value} {self.period_kind})'

    # 期間の決定（指定がなければ “今日/今週/月” を自動補完）
    def _default_bounds(self, today=None):
        from datetime import timedelta
        tz_today = today or timezone.localdate()
        if self.period_kind == self.PERIOD_DAILY:
            start = self.start_date or tz_today
            end   = self.end_date   or start
        elif self.period_kind == self.PERIOD_WEEKLY:
            start = self.start_date or (tz_today - timedelta(days=tz_today.weekday()))
            end   = self.end_date   or (start + timedelta(days=6))
        elif self.period_kind == self.PERIOD_MONTHLY:
            start = self.start_date or tz_today.replace(day=1)
            if self.end_date:
                end = self.end_date
            else:
                # 月末
                if start.month == 12:
                    end = start.replace(year=start.year+1, month=1, day=1) - timedelta(days=1)
                else:
                    end = start.replace(month=start.month+1, day=1) - timedelta(days=1)
        else:
            start = self.start_date or tz_today
            end   = self.end_date   or start
        return start, end

    def period_bounds(self, today=None):
        s, e = self._default_bounds(today)
        if self.start_date and s < self.start_date: s = self.start_date
        if self.end_date   and e > self.end_date:   e = self.end_date
        return s, e

    def save(self, *args, **kwargs):
        # custom以外/未設定は期間を埋めておく
        if not self.start_date or (self.period_kind != self.PERIOD_CUSTOM and not self.end_date):
            s, e = self._default_bounds()
            if not self.start_date: self.start_date = s
            if not self.end_date:   self.end_date   = e
        super().save(*args, **kwargs)

    # 現在値の集計（既存テーブルだけで算出）
    def current_value(self, on_date=None):
        s, e = self.period_bounds(on_date)

        if self.metric == self.METRIC_REVENUE:
            # 担当売上 = Σ(price * qty)
            return int(BillItem.objects.filter(
                served_by_cast_id=self.cast_id,
                bill__opened_at__date__range=(s, e),
                bill__table__store=self.cast.store,
            ).aggregate(
                x=Sum(ExpressionWrapper(F('price') * F('qty'), output_field=IntegerField()))
            )['x'] or 0)

        if self.metric == self.METRIC_NOMINATIONS:
            # 本指名：入店イベント数（期間内にenteredのnom）
            return int(BillCastStay.objects.filter(
                cast_id=self.cast_id, stay_type='nom',
                entered_at__date__range=(s, e),
                bill__table__store=self.cast.store,
            ).count())

        if self.metric == self.METRIC_INHOUSE:
            # 場内指名：入店イベント数（期間内にenteredのin）
            return int(BillCastStay.objects.filter(
                cast_id=self.cast_id, stay_type='in',
                entered_at__date__range=(s, e),
                bill__table__store=self.cast.store,
            ).count())

        if self.metric in (self.METRIC_CHAMP_REVENUE, self.METRIC_CHAMP_COUNT):
            qs = BillItem.objects.filter(
                bill__opened_at__date__range=(s, e),
                bill__table__store=self.cast.store,
                item_master__category__code__in=['champagne', 'original-champagne'],
                served_by_cast_id=self.cast_id,
            )
            if self.metric == self.METRIC_CHAMP_REVENUE:
                return int(qs.aggregate(
                    x=Sum(ExpressionWrapper(F('price') * F('qty'), output_field=IntegerField()))
                )['x'] or 0)
            else:  # METRIC_CHAMP_COUNT
                return int(qs.aggregate(x=Sum('qty'))['x'] or 0)

        return 0

    def progress(self, on_date=None):
        cur = self.current_value(on_date)
        tgt = int(self.target_value or 0)
        ratio = (cur / tgt) if tgt > 0 else 0.0
        pct   = int(ratio * 100)
        hits  = [m for m in self.MILESTONES if pct >= m]
        return {'value': cur, 'ratio': ratio, 'percent': pct, 'hits': hits}

    def record_new_hits(self, on_date=None):
        """未通知のマイルストーンがあれば milestones_hit を更新して返す"""
        pr = self.progress(on_date)
        cur = set(self.milestones_hit or [])
        new = [m for m in pr['hits'] if m not in cur]
        if new:
            self.milestones_hit = sorted(cur.union(new))
            self.save(update_fields=['milestones_hit','updated_at'])
        return new, pr



class BillDiscountLine(models.Model):
    """
    手入力の割引明細（ラベル＋金額）。
    - 常に「減額」を表す前提なので、amount は正の整数（円）。
    - 並び順は sort_order → id の順。
    """
    bill = models.ForeignKey('billing.Bill', on_delete=models.CASCADE,
                             related_name='manual_discounts')
    label = models.CharField('割引明細', max_length=120)
    amount = models.PositiveIntegerField('金額（円・正の値）')
    sort_order = models.PositiveIntegerField('表示順', default=0)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '手入力割引明細'
        verbose_name_plural = verbose_name
        ordering = ('sort_order', 'id')

    def __str__(self):
        return f'{self.label}: -¥{self.amount:,}'


# ═══════════════════════════════════════════════════════════════════
# 時間別売上サマリ（リアルタイム集計）
# ═══════════════════════════════════════════════════════════════════
class HourlySalesSummary(models.Model):
    """
    時間別売上サマリ（1店舗 x 1日 x 1時間）
    Bill.close() 時に Bill.closed_at の時刻で自動更新
    """
    store = models.ForeignKey('billing.Store', on_delete=models.CASCADE, related_name='hourly_summaries')
    date = models.DateField(db_index=True, help_text='集計日（YYYY-MM-DD）')
    hour = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        help_text='時刻（0-23）'
    )
    
    # 全体集計
    sales_total = models.PositiveIntegerField(default=0, help_text='売上合計')
    bill_count = models.PositiveIntegerField(default=0, help_text='伝票数')
    customer_count = models.PositiveIntegerField(default=0, help_text='来客数')
    
    # カテゴリ別内訳
    sales_set = models.PositiveIntegerField(default=0, help_text='セット売上')
    sales_drink = models.PositiveIntegerField(default=0, help_text='ドリンク売上')
    sales_food = models.PositiveIntegerField(default=0, help_text='フード売上')
    sales_champagne = models.PositiveIntegerField(default=0, help_text='シャンパン売上')
    
    # メタ
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('store', 'date', 'hour')
        indexes = [
            models.Index(fields=['store', 'date', 'hour']),
            models.Index(fields=['date', 'hour']),
        ]
    
    def __str__(self):
        return f"{self.store.name} {self.date} {self.hour:02d}:00"
    
    @property
    def is_within_business_hours(self) -> bool:
        """この時間帯が営業時間内かチェック（営業日ベース）"""
        # 営業日時刻に変換（日中の時刻 → cutoff前なら +24）
        hour_relative = Decimal(str(self.hour))
        if self.hour < self.store.business_day_cutoff_hour:
            hour_relative += 24
        
        return self.store.business_open_hour <= hour_relative <= self.store.business_close_hour

        verbose_name = '時間別売上サマリ'
        verbose_name_plural = verbose_name
        ordering = ['date', 'hour']
    
    def __str__(self):
        return f'{self.store.name} {self.date} {self.hour:02d}:00 - ¥{self.sales_total:,}'


class HourlyCastSales(models.Model):
    """
    時間別キャスト売上（1店舗 x 1日 x 1時間 x 1キャスト）
    HourlySalesSummary の内訳として、キャスト別の売上を記録
    """
    hourly_summary = models.ForeignKey(
        'billing.HourlySalesSummary',
        on_delete=models.CASCADE,
        related_name='cast_breakdown'
    )
    cast = models.ForeignKey('billing.Cast', on_delete=models.CASCADE, related_name='hourly_sales')
    
    # キャスト別集計
    sales_total = models.PositiveIntegerField(default=0, help_text='このキャストの売上合計')
    sales_nom = models.PositiveIntegerField(default=0, help_text='本指名売上')
    sales_in = models.PositiveIntegerField(default=0, help_text='場内指名売上')
    sales_free = models.PositiveIntegerField(default=0, help_text='フリー売上')
    sales_champagne = models.PositiveIntegerField(default=0, help_text='シャンパン売上')
    
    bill_count = models.PositiveIntegerField(default=0, help_text='担当伝票数')
    
    class Meta:
        unique_together = ('hourly_summary', 'cast')
        indexes = [
            models.Index(fields=['cast', 'hourly_summary']),
        ]
        verbose_name = '時間別キャスト売上'
        verbose_name_plural = verbose_name
        ordering = ['-sales_total']
    
    def __str__(self):
        return f'{self.cast.stage_name} {self.hourly_summary.date} {self.hourly_summary.hour:02d}:00 - ¥{self.sales_total:,}'