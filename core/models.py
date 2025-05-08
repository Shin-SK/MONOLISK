from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.utils.translation import gettext_lazy as _

# ---------- 共通 ──────────
class TimeStamped(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	class Meta:
		abstract = True

# ---------- ユーザー ----------
class User(AbstractUser):
	email = models.EmailField(_('email address'), unique=True)
	# ロールは Django Group を利用（STAFF / DRIVER / CAST）
	def add_role(self, role_name: str):
		g, _ = Group.objects.get_or_create(name=role_name.upper())
		self.groups.add(g)

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
class Cast(TimeStamped):
	class PriceMode(models.TextChoices):
		DEFAULT = 'DEFAULT','Default'
		MARKET  = 'MARKET', 'Market'
	name		= models.CharField(max_length=50)
	store	   = models.ForeignKey(Store,on_delete=models.CASCADE)
	rank		= models.ForeignKey(Rank, on_delete=models.CASCADE)
	star_count  = models.PositiveSmallIntegerField(default=0)
	price_mode  = models.CharField(max_length=10, choices=PriceMode.choices, default=PriceMode.DEFAULT)
	def __str__(self):
		return self.name


class CastCoursePrice(TimeStamped):
	cast	= models.ForeignKey(Cast,   on_delete=models.CASCADE)
	course  = models.ForeignKey(Course, on_delete=models.CASCADE)
	custom_price = models.PositiveIntegerField()

class CastOption(TimeStamped):
	cast	= models.ForeignKey(Cast,   on_delete=models.CASCADE)
	option  = models.ForeignKey(Option, on_delete=models.CASCADE)
	custom_price = models.PositiveIntegerField(null=True, blank=True)
	is_enabled   = models.BooleanField(default=True)

# ---------- 顧客・ドライバー ----------
class Driver(TimeStamped):
	user  = models.OneToOneField(User, on_delete=models.CASCADE)
	store = models.ForeignKey(Store, on_delete=models.CASCADE)
	def __str__(self):
		return self.name


class Customer(TimeStamped):
	name	= models.CharField(max_length=60)
	phone   = models.CharField(max_length=20)
	address = models.CharField(max_length=255, blank=True)
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
	discrepancy_flag   = models.BooleanField(default=False)

	# ──簡易プロパティ──
	@property
	def expected_amount(self):
		lines = sum(rc.total_price for rc in self.casts.all())
		charges = sum(c.amount for c in self.charges.all())
		return lines + charges + self.manual_extra_price

class ReservationCast(TimeStamped):
	reservation = models.ForeignKey(Reservation, related_name='casts', on_delete=models.CASCADE)
	cast		= models.ForeignKey(Cast, on_delete=models.CASCADE)
	rank_course = models.ForeignKey(RankCourse, on_delete=models.CASCADE)

	@property
	def total_price(self):
		price = self.rank_course.base_price
		price += self.rank_course.star_increment * self.cast.star_count
		# market 上書き
		override = CastCoursePrice.objects.filter(cast=self.cast, course=self.rank_course.course).first()
		if override: price = override.custom_price
		return price

class ReservationCharge(TimeStamped):
	class Kind(models.TextChoices):
		OPTION   = 'OPTION',   'Option'
		DISCOUNT = 'DISCOUNT', 'Discount'
		EXTEND   = 'EXTEND',   'Extension'
		CANCEL   = 'CANCEL_FEE','Cancel Fee'
		SPECIAL  = 'SPECIAL_PRICE','Special'
	reservation = models.ForeignKey(Reservation, related_name='charges', on_delete=models.CASCADE)
	kind		= models.CharField(max_length=15, choices=Kind.choices)
	ref_id	  = models.PositiveIntegerField(null=True, blank=True)  # Option.id 等
	amount	  = models.IntegerField()  # ±

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
