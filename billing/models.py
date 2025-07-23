# billing/models.py  ※TAB インデント
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField
from django.db.models import Sum 

User = get_user_model()

class UserStore(models.Model):
	"""
	1ユーザー = 1店舗 の紐付けだけを保持する軽量プロファイル
	"""
	user  = models.OneToOneField(
		User, on_delete=models.CASCADE,
		related_name='store_profile'
	)
	store = models.ForeignKey('billing.Store', on_delete=models.CASCADE)

	class Meta:
		verbose_name = 'ユーザー店舗紐付け'
		verbose_name_plural = verbose_name

	def __str__(self):
		return f'{self.user.username} → {self.store.name}'


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
	tax_rate	 = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.10'))
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
	code  = models.CharField(max_length=20, primary_key=True)	  # 'set' 'drink' …
	name  = models.CharField(max_length=30)
	back_rate_free	   = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
	back_rate_nomination = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
	back_rate_inhouse	= models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.30'))
	def __str__(self): return self.name


class Cast(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='ユーザー'
    )
    stage_name = models.CharField('源氏名', max_length=50)
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
	name	  = models.CharField(max_length=40)
	price_regular = models.PositiveIntegerField()
	price_late	= models.PositiveIntegerField(null=True, blank=True)
	apply_service	   = models.BooleanField(default=True)
	exclude_from_payout = models.BooleanField(default=False)
	track_stock		 = models.BooleanField(default=False)
	code = models.CharField(max_length=30, blank=True, db_index=True)
	category	 = models.CharField(
		max_length=8,
		choices=[('set','セット'), ('ext','延長'), ('drink','ドリンク')],
		default='drink'
	)
	duration_min   = models.PositiveSmallIntegerField(default=0)
	def __str__(self): return self.name


class ItemStock(models.Model):
	item = models.OneToOneField(ItemMaster, on_delete=models.CASCADE, related_name='stock')
	qty  = models.IntegerField(default=0)
	def __str__(self): return f'{self.item.name}: {self.qty}'


# ───────── 伝票 ─────────
class Bill(models.Model):
	table			= models.ForeignKey(Table, on_delete=models.CASCADE, null=True, blank=True,)
	opened_at		= models.DateTimeField(default=timezone.now)
	closed_at		= models.DateTimeField(null=True, blank=True)
	nominated_casts  = models.ManyToManyField(Cast, blank=True, related_name='nominated_bills')

	subtotal		= models.PositiveIntegerField(default=0)
	service_charge  = models.PositiveIntegerField(default=0)
	tax			 = models.PositiveIntegerField(default=0)
	grand_total	 = models.PositiveIntegerField(default=0)

	total		   = models.PositiveIntegerField(default=0)  # → close 時に確定

	settled_total  = models.PositiveIntegerField( null=True, blank=True, default=None)  # None＝未入力

	# -------------------------------------------------
	# ★ 計算ロジックを 1 箇所に集約
	# -------------------------------------------------
	def recalc(self, save=False):
		"""Items を集計して金額3点 + grand_total を更新  
		   `save=True` を渡すとこの場で保存まで行う
		"""
		sub = sum(it.subtotal for it in self.items.all())

		# 店舗ごとの料率を Decimal(0‑1) で取得
		store = self.table.store if self.table_id else None
		sr = Decimal(store.service_rate) if store else Decimal('0')
		tr = Decimal(store.tax_rate)	  if store else Decimal('0')
		sr = sr/100 if sr >= 1 else sr	# 1 以上なら “％” 表示とみなし÷100
		tr = tr/100 if tr >= 1 else tr

		svc = int( (Decimal(sub) * sr).quantize(Decimal('1'),
												ROUND_HALF_UP) )
		tax = int( (Decimal(sub + svc) * tr).quantize(Decimal('1'),
													  ROUND_HALF_UP) )
		self.subtotal	   = sub
		self.service_charge = svc
		self.tax			= tax
		self.grand_total	= sub + svc + tax
		if save:
			self.save(update_fields=['subtotal', 'service_charge',
									 'tax', 'grand_total'])
		return self.grand_total

	def close(self):
		from .services import calc_bill_totals
		res			= calc_bill_totals(self)
		self.total	 = res['total']
		self.closed_at = timezone.now()
		self.save()
		self.payouts.all().delete()
		for cast, amt in res['payouts'].items():
			CastPayout.objects.create(bill=self, cast=cast, amount=amt)


class BillCastStay(models.Model):
	STAY_TYPE = [
		('free', 'フリー'),	  # 付け回し・フリー
		('in',   '場内指名'),
		('nom',  '本指名'),
	]
	bill = models.ForeignKey(
		Bill, on_delete=models.CASCADE, related_name='stays'
	)
	cast	   = models.ForeignKey(Cast, on_delete=models.CASCADE)
	entered_at = models.DateTimeField()
	left_at	= models.DateTimeField(null=True, blank=True)
	stay_type  = models.CharField(
		max_length=4, choices=STAY_TYPE, default='free'
	)
	is_inhouse = models.BooleanField(null=True, blank=True)
	class Meta:
		ordering = ['entered_at']


# ───────── 品目行 ─────────
class BillItem(models.Model):
	bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
	item_master = models.ForeignKey(ItemMaster, null=True, blank=True, on_delete=models.SET_NULL)
	name  = models.CharField(max_length=40, blank=True)
	price = models.PositiveIntegerField(null=True, blank=True)
	qty   = models.PositiveSmallIntegerField(default=1)
	served_by_cast = models.ForeignKey(Cast, null=True, blank=True, on_delete=models.SET_NULL)

	# フラグ
	is_nomination   = models.BooleanField(default=False, null=True)   # ★本指名ドリンク等
	is_inhouse	  = models.BooleanField(default=False, null=True)   # ◯場内指名ドリンク
	exclude_from_payout = models.BooleanField(default=False, null=True)

	class Meta:
		ordering = ['id']

	@property
	def back_rate(self):
		cat = self.item_master.category
		# 優先順: キャスト個別→カテゴリ既定
		if self.is_nomination:
			return (
				self.served_by_cast.back_rate_nomination_override
				or cat.back_rate_nomination
			)
		elif self.is_inhouse:
			return (
				self.served_by_cast.back_rate_inhouse_override
				or cat.back_rate_inhouse
			)
		else:  # フリー
			return (
				self.served_by_cast.back_rate_free_override
				or cat.back_rate_free
			)

	def __str__(self): return f'{self.name} ×{self.qty}'

	@property
	def subtotal(self):
		return (self.price or 0) * (self.qty or 0)

	def save(self, *args, **kwargs):
		if self.item_master:
			if not self.name:
				self.name = self.item_master.name
			if not self.price:
				self.price = self.item_master.price_regular
			if self.item_master.exclude_from_payout:
				self.exclude_from_payout = True
		# ↓ ここを消す（プロパティには代入できない）
		# self.subtotal = (self.price or 0) * (self.qty or 0)
		super().save(*args, **kwargs)


class CastPayout(models.Model):
	bill_item = models.ForeignKey(BillItem, null=True, blank=True,
								  on_delete=models.CASCADE, related_name='payouts')
	bill	  = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payouts', null=True)
	cast	  = models.ForeignKey(Cast, on_delete=models.CASCADE, null=True)
	amount	= models.PositiveIntegerField()
	def __str__(self): return f'{self.cast}: ¥{self.amount}'
