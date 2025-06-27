from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.templatetags.static import static
from django.utils import timezone


# ---------- 共通 ──────────
class TimeStamped(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	class Meta:
		abstract = True

# ---------- ユーザー ----------
class User(AbstractUser):
	email = models.EmailField(_('email address'), unique=True)
	display_name = models.CharField(
		max_length=50,
		blank=True,
		verbose_name=_('Display name')
	)
	avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)  # ★追加

	@property
	def avatar_url(self) -> str:
		if self.avatar:
			return self.avatar.url
		return settings.STATIC_URL + 'img/user-default.png'

	# ロールは Django Group を利用（STAFF / DRIVER / CAST）
	def add_role(self, role_name: str):
		g, _ = Group.objects.get_or_create(name=role_name.upper())
		self.groups.add(g)

	# 管理画面などで分かりやすくq
	def __str__(self):
		return self.display_name or self.username

# ---------- マスタ ----------
class Store(TimeStamped):
	name	= models.CharField(max_length=50)
	address = models.CharField(max_length=255)
	def __str__(self):
		return self.name

class Rank(TimeStamped):
	name = models.CharField(max_length=30)
	def __str__(self):
		return self.name

class Course(TimeStamped):
	minutes  = models.PositiveSmallIntegerField()
	is_pack  = models.BooleanField(default=False)  # True=コミコミパック
	def __str__(self):
		label = f"{self.minutes}min"
		return f"{label} (Pack)" if self.is_pack else label

class RankCourse(TimeStamped):
	store	   = models.ForeignKey(Store, on_delete=models.CASCADE)
	rank		= models.ForeignKey(Rank,  on_delete=models.CASCADE)
	course	  = models.ForeignKey(Course,on_delete=models.CASCADE)
	base_price  = models.PositiveIntegerField()
	star_increment = models.PositiveIntegerField(default=0)  # ☆1個あたり
	def __str__(self):
		return f"{self.course.minutes}min ({self.rank.name})"

class Option(TimeStamped):

	class Category(models.TextChoices):
		OTHER = 'OTHER', 'その他'
		GROUP  = 'GROUP',  '3P/4P'
		DISCOUNT = 'DISCOUNT','割引'
		OPTIONS = 'OPTIONS','オプション'
	name		   = models.CharField(max_length=50)
	default_price  = models.PositiveIntegerField()
	category	   = models.CharField(max_length=20, choices=Category.choices)
	def __str__(self):
		return self.name

	class Meta:
		verbose_name = 'オプション'
		verbose_name_plural = 'オプション'
	

class GroupOptionPrice(TimeStamped):
	store		= models.ForeignKey(Store, on_delete=models.CASCADE)
	participants = models.PositiveSmallIntegerField()  # 3 or 4
	course	   = models.ForeignKey(Course, on_delete=models.CASCADE)
	price		= models.PositiveIntegerField()

# ---------- キャスト ----------

# ---------- Performer（本名で一意） ----------
class Performer(TimeStamped):
	real_name  = models.CharField(max_length=60)
	birthday   = models.DateField(null=True, blank=True)
	# 将来: bank_account, id_card_photo 等
	def __str__(self):
		return self.real_name

	class Meta:
		verbose_name = '予約'
		verbose_name_plural = '予約'

# ---------- CastProfile（旧 Cast を分割） ----------
class CastProfile(TimeStamped):
	performer  = models.ForeignKey(Performer, on_delete=models.CASCADE)
	store	  = models.ForeignKey(Store, on_delete=models.CASCADE)
	stage_name = models.CharField(max_length=50)		  # 源氏名
	rank	   = models.ForeignKey(Rank, on_delete=models.CASCADE)
	star_count = models.PositiveSmallIntegerField(default=0)
	memo = models.TextField(blank=True) 
	ng_customers = models.ManyToManyField('Customer', blank=True, related_name='ng_casts_of')
	photo = models.ImageField(upload_to='cast_photos/', null=True, blank=True)
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='cast_profiles',
		help_text='このログインで管理画面・マイページに入れるキャストなら紐付ける'
	)

	class PriceMode(models.TextChoices):
		DEFAULT = 'DEFAULT', 'Default'
		MARKET  = 'MARKET',  'Market'

	price_mode = models.CharField(
		max_length=10, choices=PriceMode.choices, default=PriceMode.DEFAULT
	)

	class Meta:
		unique_together = ("performer", "store")
		verbose_name = 'キャスト情報'
		verbose_name_plural = 'キャスト情報'

	def __str__(self):
		return f"{self.stage_name} @ {self.store.name}"

	@property
	def photo_url(self) -> str:
		if self.photo:
			return self.photo.url
		return static("img/cast-default.png")



class CastCoursePrice(TimeStamped):
	cast_profile = models.ForeignKey(CastProfile, on_delete=models.CASCADE)
	course	   = models.ForeignKey(Course, on_delete=models.CASCADE)
	custom_price = models.PositiveIntegerField(null=True, blank=True)

class CastOption(TimeStamped):
	cast_profile = models.ForeignKey(CastProfile, on_delete=models.CASCADE)
	option	   = models.ForeignKey(Option, on_delete=models.CASCADE)
	custom_price = models.PositiveIntegerField(null=True, blank=True)
	is_enabled   = models.BooleanField(default=True)


# ---------- 顧客・ドライバー ----------
class Driver(TimeStamped):
	user  = models.OneToOneField(User, on_delete=models.CASCADE)
	store = models.ForeignKey(Store, on_delete=models.CASCADE)
	def __str__(self):
		return str(self.user)

# ---------- 顧客 ----------
class Customer(TimeStamped):
	name	= models.CharField(max_length=60)
	phone = models.CharField(max_length=20, db_index=True, unique=True)
	memo	= models.TextField(blank=True)
	def __str__(self):
		return self.name

	class Meta:
		verbose_name = '顧客'
		verbose_name_plural = '顧客'

class CustomerAddress(TimeStamped):
	customer		= models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
	label			= models.CharField(max_length=30, blank=True)
	address			= models.CharField(max_length=255)
	is_primary		= models.BooleanField(default=False)

	class Meta:
		verbose_name = '顧客住所'
		verbose_name_plural = '顧客住所'
		unique_together = ('customer', 'address')

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		# is_primary が立ったら他を倒す
		if self.is_primary:
			self.customer.addresses.exclude(id=self.id).update(is_primary=False)



# ---------- 予約 ----------
class Reservation(TimeStamped):

	class Status(models.TextChoices):
		BOOKED	 = 'BOOKED', 'Booked'
		CONFIRMED  = 'CONFIRMED','Confirmed'
		INSERVICE  = 'INSERVICE','In Service'
		CLOSED	 = 'CLOSED',  'Closed'
		CANCELED   = 'CANCELED','Canceled'

	store	 = models.ForeignKey(Store,  on_delete=models.CASCADE, verbose_name='店舗',)
	driver	= models.ForeignKey(Driver, on_delete=models.SET_NULL, verbose_name='ドライバー', null=True, blank=True,)
	customer  = models.ForeignKey(Customer,on_delete=models.CASCADE, verbose_name='顧客')
	start_at  = models.DateTimeField(verbose_name='開始時刻')
	total_time= models.PositiveSmallIntegerField()  # 分
	status	= models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED , verbose_name='ステータス')
	manual_extra_price = models.IntegerField(default=0, verbose_name='延長料金')
	received_amount   = models.IntegerField(null=True, blank=True, verbose_name='受取金')
	discrepancy_flag  = models.BooleanField(default=False)
	deposited_amount = models.PositiveIntegerField(default=0)
	address_text	= models.CharField(max_length=255, null=True, blank=True,)
	address_book	= models.ForeignKey(
		CustomerAddress, null=True, blank=True,
		on_delete=models.SET_NULL, related_name='reservations'
	)
	TYPE_NORMAL, TYPE_PRINCESS = "normal", "hime"
	RES_TYPE_CHOICES = [
		(TYPE_NORMAL,   "通常予約"),
		(TYPE_PRINCESS, "姫予約"),
	]
	reservation_type = models.CharField(
		max_length=10, choices=RES_TYPE_CHOICES, default=TYPE_NORMAL
	)

	# ───────── 合計ヘルパ ─────────
	def total_revenue(self) -> int:
		return sum(e.amount for e in self.manual_entries.filter(entry_type=ManualEntry.REVENUE))

	def total_expense(self) -> int:
		return sum(e.amount for e in self.manual_entries.filter(entry_type=ManualEntry.EXPENSE))

	def net_total(self) -> int:
		return self.total_revenue() - self.total_expense() + sum(p.amount for p in self.payments.all())


	# ──簡易プロパティ──
	@property
	def expected_amount(self):
		lines	 = sum((rc.total_price or 0) for rc in self.casts.all())	# ← None 逃し
		charges	 = sum((c.amount		  or 0) for c  in self.charges.all())
		return lines + charges + self.manual_extra_price

	# 受取額が変更されたら差額フラグを更新
	def save(self, *args, **kwargs):
		if self.received_amount is not None:
			self.discrepancy_flag = (self.received_amount != self.expected_amount)
		super().save(*args, **kwargs)

	class Meta:
		verbose_name = '予約'
		verbose_name_plural = '予約'

class ReservationCast(TimeStamped):
	reservation  = models.ForeignKey(
		Reservation, on_delete=models.CASCADE,
		related_name="casts",
		verbose_name=_('予約')
	)
	cast_profile = models.ForeignKey(
		CastProfile, on_delete=models.CASCADE,
		verbose_name=_('キャスト')
	)
	course	   = models.ForeignKey(				   # ← 追加済み
		Course, on_delete=models.CASCADE,
		null=True, blank=True,
		verbose_name=_('コース')
	)
	rank_course  = models.ForeignKey(
		RankCourse, on_delete=models.CASCADE,
		null=True, blank=True, editable=False
	)

	class Meta:
		verbose_name = _('キャスト')
		verbose_name_plural = _('キャスト')

	def save(self, *args, **kwargs):
		"""
		cast_profile・course が揃ったら自動で RankCourse を決定
		"""
		if self.cast_profile_id and self.course_id and not self.rank_course_id:
			try:
				self.rank_course = RankCourse.objects.get(
					store  = self.reservation.store,
					rank   = self.cast_profile.rank,
					course = self.course
				)
			except RankCourse.DoesNotExist:
				from django.core.exceptions import ValidationError
				raise ValidationError("RankCourse が未登録です")

		super().save(*args, **kwargs)

	@property
	def total_price(self):
		# ① 基本価格
		price = self.rank_course.base_price
		price += self.rank_course.star_increment * self.cast_profile.star_count   # ← 修正

		# ② 個別上書き
		override = CastCoursePrice.objects.filter(
			cast_profile=self.cast_profile,		  # ← 修正
			course=self.rank_course.course
		).first()

		if override and override.custom_price is not None:
			price = override.custom_price

		return price


class ReservationCharge(TimeStamped):
	# ①「何の行か」をフィールドで分ける
	option		= models.ForeignKey(
		Option, null=True, blank=True, on_delete=models.SET_NULL
	)
	extend_course = models.ForeignKey(
		RankCourse, null=True, blank=True, on_delete=models.SET_NULL
	)
	# ※ 割引の「参照先」が無い場合はどちらも None で OK

	class Kind(models.TextChoices):
		OPTION   = 'OPTION',   'Option'
		DISCOUNT = 'DISCOUNT', 'Discount'
		EXTEND   = 'EXTEND',   'Extension'

	reservation = models.ForeignKey(
		Reservation, related_name='charges', on_delete=models.CASCADE
	)
	kind   = models.CharField(max_length=10, choices=Kind.choices)
	amount = models.IntegerField(null=True, blank=True,)

	def clean(self):
		"""
		kind ごとに必須 FK をチェック
		"""
		from django.core.exceptions import ValidationError
		if self.kind == 'OPTION' and not self.option_id:
			raise ValidationError({'option': 'Option を選んでください'})
		if self.kind == 'EXTEND' and not self.extend_course_id:
			raise ValidationError({'extend_course': '延長コースを選んでください'})


class CashFlow(TimeStamped):
	class Type(models.TextChoices):
		EXPECTED	  = 'EXPECTED', 'Expected'
		CAST_ADVANCE  = 'CAST_ADVANCE','Cast Advance'
		SHOP_DEPOSIT  = 'SHOP_DEPOSIT','Shop Deposit'
		REFUND		= 'REFUND','Refund'
	reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
	type   = models.CharField(max_length=20, choices=Type.choices)
	amount = models.IntegerField()
	recorded_at = models.DateTimeField(auto_now_add=True)



class ShiftPlan(models.Model):
	"""
	出勤『予定』
	1キャスト・1日につき1件想定（複数帯対応が要るなら Unique を外す）
	"""
	cast_profile = models.ForeignKey(
		"CastProfile", on_delete=models.CASCADE, related_name="shift_plans"
	)
	store = models.ForeignKey("Store", on_delete=models.CASCADE)
	date  = models.DateField(db_index=True)
	start_at = models.TimeField()
	end_at   = models.TimeField()
	memo	 = models.TextField(blank=True)

	class Meta:
		unique_together = ("cast_profile", "date")  # 予定は１日１本
		ordering = ["date", "start_at"]

	def __str__(self):
		return f"{self.cast_profile} {self.date} {self.start_at}-{self.end_at}"


class ShiftAttendance(models.Model):
	"""
	出勤『実績』（打刻）
	予定なしで当日飛び込み＝ shift_plan=NULL も許可
	"""
	shift_plan = models.OneToOneField(
		ShiftPlan, null=True, blank=True,
		on_delete=models.SET_NULL, related_name="attendance"
	)
	cast_profile = models.ForeignKey(
		"CastProfile", on_delete=models.CASCADE, related_name="attendances"
	)
	checked_in	  = models.BooleanField(default=False)
	checked_in_at   = models.DateTimeField(null=True, blank=True)
	checked_out_at  = models.DateTimeField(null=True, blank=True)
	note			= models.TextField(blank=True)

	def checkin(self):
		self.checked_in = True
		self.checked_in_at = timezone.now()
		self.save(update_fields=["checked_in", "checked_in_at"])

	class Meta:
		ordering = ["-checked_in_at"]

	def __str__(self):
		return f"{self.cast_profile} @ {self.checked_in_at or '---'}"





# 既存 import 群のあとに追記
class ReservationDriver(models.Model):
	"""予約 1 件に対して最大 2 行（PU / DO or BOTH）"""
	class Role(models.TextChoices):
		PICK_UP   = "PU", _("Pick-Up")
		DROP_OFF  = "DO", _("Drop-Off")
		BOTH	  = "BO", _("Both")	  # PU=DO 同一ドライバー用

	class Status(models.TextChoices):
		PLANNED	  = "PL", _("Planned")
		IN_PROGRESS  = "IP", _("In Progress")
		DONE		 = "DN", _("Done")

	reservation   = models.ForeignKey(
		"Reservation", related_name="drivers",
		on_delete=models.CASCADE
	)
	driver		= models.ForeignKey(
		"Driver", on_delete=models.PROTECT, related_name="reservations"
	)
	role		  = models.CharField(
		max_length=2, choices=Role.choices, default=Role.PICK_UP
	)
	start_at	  = models.DateTimeField(null=True, blank=True)
	end_at		= models.DateTimeField(null=True, blank=True)
	collected_amount = models.PositiveIntegerField(
		null=True, blank=True, help_text="DO 時の現金回収額"
	)
	status		= models.CharField(
		max_length=2, choices=Status.choices, default=Status.PLANNED
	)

	class Meta:
		unique_together = ("reservation", "role")  # PU は 1 行、DO は 1 行
		ordering = ["start_at", "role"]

	def __str__(self):
		return f"{self.reservation_id}:{self.get_role_display()} by {self.driver}"



class Payment(models.Model):
	CARD, CASH = "card", "cash"
	METHOD_CHOICES = [(CARD, "カード"), (CASH, "現金")]

	reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="payments")
	method	  = models.CharField(max_length=5, choices=METHOD_CHOICES)
	amount	  = models.PositiveIntegerField()


class ManualEntry(models.Model):
	REVENUE, EXPENSE = "revenue", "expense"
	TYPE_CHOICES = [
		(REVENUE, "売上"),   # 例: 延長料金・飛び込みオプションなど
		(EXPENSE, "経費"),   # 例: 罰金・立替・雑費など
	]

	reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="manual_entries")
	entry_type  = models.CharField(max_length=7, choices=TYPE_CHOICES)
	label	   = models.CharField(max_length=50)
	amount	  = models.PositiveIntegerField()

	class Meta:
		ordering = ["id"]