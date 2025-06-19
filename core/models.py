from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.templatetags.static import static

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
		unique_together = ("performer", "store")		  # 同じ店で別名禁止

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


class Customer(TimeStamped):
	name	= models.CharField(max_length=60)
	phone = models.CharField(max_length=20, db_index=True, unique=True)
	address = models.CharField(max_length=255, blank=True)
	memo	= models.TextField(blank=True)
	def __str__(self):
		return self.name


# ---------- 予約 ----------
class Reservation(TimeStamped):
	class Status(models.TextChoices):
		BOOKED	 = 'BOOKED', 'Booked'
		CONFIRMED  = 'CONFIRMED','Confirmed'
		INSERVICE  = 'INSERVICE','In Service'
		CLOSED	 = 'CLOSED',  'Closed'
		CANCELED   = 'CANCELED','Canceled'

	store	 = models.ForeignKey(Store,  on_delete=models.CASCADE)
	driver	= models.ForeignKey(Driver, on_delete=models.CASCADE)
	customer  = models.ForeignKey(Customer,on_delete=models.CASCADE)
	start_at  = models.DateTimeField()
	total_time= models.PositiveSmallIntegerField()  # 分
	status	= models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
	manual_extra_price = models.IntegerField(default=0)
	received_amount   = models.IntegerField(null=True, blank=True)
	discrepancy_flag  = models.BooleanField(default=False)
	deposited_amount = models.PositiveIntegerField(default=0)


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

class ReservationCast(TimeStamped):
	reservation   = models.ForeignKey(Reservation, related_name='casts', on_delete=models.CASCADE)
	cast_profile  = models.ForeignKey(CastProfile, on_delete=models.CASCADE)
	rank_course   = models.ForeignKey(RankCourse, on_delete=models.CASCADE)

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
