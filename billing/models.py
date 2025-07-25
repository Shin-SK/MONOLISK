# billing/models.py  ※TAB インデント
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField
from django.db.models import Sum 
from django.db.models.signals import post_delete
from django.dispatch import receiver
from datetime import timedelta

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
		proxy = True				# DB テーブルはそのまま
		app_label = 'billing'	   # ★ここを偽装するとサイドバーの見出しが billing になる
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
		'アバター',				# ← 第1引数にラベル
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
	stores = models.ManyToManyField(		  # 将来の“複数店舗兼務”に備えて M2M
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

	# 退店予定時刻（SET／延長を追加・削除したら自動更新）
	expected_out = models.DateTimeField('退店予定', null=True, blank=True)

	nominated_casts = models.ManyToManyField('billing.Cast', blank=True, related_name='nominated_bills')

	subtotal = models.PositiveIntegerField(default=0)
	service_charge = models.PositiveIntegerField(default=0)
	tax = models.PositiveIntegerField(default=0)
	grand_total = models.PositiveIntegerField(default=0)

	total = models.PositiveIntegerField(default=0)		  # close 時に確定
	settled_total = models.PositiveIntegerField(null=True, blank=True, default=None)
	
	@property
	def set_rounds(self):
		"""SET 行の行数（ラウンド数）"""
		return self.items.filter(item_master__code__startswith='set').count()

	@property
	def ext_minutes(self):
		"""延長系の総分数"""
		return sum(
			(it.duration_min or 30) * it.qty
			for it in self.items.filter(item_master__code__startswith='extension')
		)
	

	# ─── 金額再計算 ───────────────────────────────
	def recalc(self, save=False):
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
	def update_expected_out(self, save=False):
		"""
		SET の 1 行目 + EXTENSION 系を積算して expected_out を再設定
		"""
		minutes = 0
		base_found = False
		for it in self.items.all():
			code = (it.code or '').lower()
			dur = it.duration_min or 0
			if code.startswith('set') and not base_found:
				base_found = True
				minutes += dur
			elif code.startswith('extension'):
				minutes += dur * it.qty

		self.expected_out = self.opened_at + timedelta(minutes=minutes) if minutes else None
		if save:
			self.save(update_fields=['expected_out'])
		return self.expected_out

	# ─── 締め処理は変更なし ───────────────────────
	def close(self):
		from .services import calc_bill_totals
		res = calc_bill_totals(self)
		self.total = res['total']
		self.closed_at = timezone.now()
		self.save()
		self.payouts.all().delete()
		for cast, amt in res['payouts'].items():
			CastPayout.objects.create(bill=self, cast=cast, amount=amt)

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
		if self.item_master:
			self.name = self.name or self.item_master.name
			self.price = self.price or self.item_master.price_regular
			if self.item_master.exclude_from_payout:
				self.exclude_from_payout = True

		super().save(*args, **kwargs)

		# SET / EXTENSION 系なら退店予定を即時更新
		if self.code.startswith(('set', 'extension')):
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


# ──────────── 信号 (念のため) ────────────
@receiver(post_delete, sender=BillItem)
def _recalc_expected_out_on_delete(sender, instance, **kwargs):
	instance.bill.update_expected_out(save=True)



class CastPayout(models.Model):
	bill_item = models.ForeignKey(BillItem, null=True, blank=True,
								  on_delete=models.CASCADE, related_name='payouts')
	bill	  = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payouts', null=True)
	cast	  = models.ForeignKey(Cast, on_delete=models.CASCADE, null=True)
	amount	= models.PositiveIntegerField()
	def __str__(self): return f'{self.cast}: ¥{self.amount}'
