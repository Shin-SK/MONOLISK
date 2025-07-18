# billing/models.py  ※TAB インデント
from django.conf import settings
from decimal import Decimal
from collections import defaultdict
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField

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
		settings.AUTH_USER_MODEL,	 # ← これなら import 時に実体不要
		on_delete=models.CASCADE,
	)
	stage_name   = models.CharField(max_length=50)
	store	   = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True)
	# 個別上書き (null=カテゴリ既定を使う)
	back_rate_free_override	   = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
	back_rate_nomination_override = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
	back_rate_inhouse_override	= models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
	avatar = CloudinaryField(
		"avatar",			  # カラム名
		folder="avatars",	  # Cloudinary 内フォルダ
		format="jpg",		  # 強制フォーマット任意
		blank=True, null=True
	)

	def __str__(self): return self.stage_name or self.user.username


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
	table			= models.ForeignKey(Table, on_delete=models.CASCADE)
	opened_at		= models.DateTimeField(default=timezone.now)
	closed_at		= models.DateTimeField(null=True, blank=True)
	nominated_casts  = models.ManyToManyField(Cast, blank=True, related_name='nominated_bills')
	total			= models.PositiveIntegerField(default=0)  # 締め時に確定
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
	def subtotal(self):  return (self.price or 0) * (self.qty or 0)

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

	def save(self, *args, **kwargs):
		if self.item_master:
			if not self.name:  self.name  = self.item_master.name
			if not self.price: self.price = self.item_master.price_regular
			if self.item_master.exclude_from_payout:
				self.exclude_from_payout = True
		super().save(*args, **kwargs)
	def __str__(self): return f'{self.name} ×{self.qty}'


class CastPayout(models.Model):
	bill_item = models.ForeignKey(BillItem, null=True, blank=True,
								  on_delete=models.CASCADE, related_name='payouts')
	bill	  = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payouts', null=True)
	cast	  = models.ForeignKey(Cast, on_delete=models.CASCADE, null=True)
	amount	= models.PositiveIntegerField()
	def __str__(self): return f'{self.cast}: ¥{self.amount}'
