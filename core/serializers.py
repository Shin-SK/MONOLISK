#serializers.py
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.db import transaction
from rest_framework import serializers
from dj_rest_auth.serializers import UserDetailsSerializer
from django.db.models import Q
from .models import (
	Store, Rank, Course, RankCourse, Option, GroupOptionPrice,
	CastProfile, CastCoursePrice, CastOption, Driver, Customer,
	Reservation, ReservationCast, ReservationCharge, CashFlow, CustomerAddress, ShiftPlan, ShiftAttendance,
	ReservationDriver
)

# ---------- マスタ ----------
class StoreSerializer(serializers.ModelSerializer):
	class Meta: model = Store; fields = '__all__'

class RankSerializer(serializers.ModelSerializer):
	class Meta: model = Rank; fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
	class Meta: model = Course; fields = '__all__'

class RankCourseSerializer(serializers.ModelSerializer):
	class Meta: model = RankCourse; fields = '__all__'

class OptionSerializer(serializers.ModelSerializer):
	class Meta: model = Option; fields = '__all__'

class GroupOptionPriceSerializer(serializers.ModelSerializer):
	class Meta: model = GroupOptionPrice; fields = '__all__'

# ---------- キャスト ----------
class CastSerializer(serializers.ModelSerializer):
	ng_customers = serializers.PrimaryKeyRelatedField(
		many=True, queryset=Customer.objects.all(), required=False
	)
	photo_url = serializers.SerializerMethodField()

	user = serializers.PrimaryKeyRelatedField(
		queryset=get_user_model().objects.all(),
		allow_null=True,
		required=False
	)

	class Meta:
		model  = CastProfile
		fields = '__all__'		  # memo, ng_customers も含まれる

	def get_photo_url(self, obj):
		request = self.context.get("request")
		url = obj.photo_url					   # property で既に絶対 or static
		return request.build_absolute_uri(url) if request else url

class CastCoursePriceSerializer(serializers.ModelSerializer):
	class Meta: model = CastCoursePrice; fields = '__all__'

class CastOptionSerializer(serializers.ModelSerializer):
	option_name = serializers.CharField(source='option.name', read_only=True)

	class Meta:
		model  = CastOption
		fields = ('id', 'option', 'option_name', 'is_enabled')

# ---------- 顧客・ドライバー ----------
class DriverListSerializer(serializers.ModelSerializer):
	name = serializers.SerializerMethodField()

	class Meta:
		model  = Driver
		fields = ('id', 'name')

	def get_name(self, obj):
		return obj.user.display_name or obj.user.username


class DriverSerializer(serializers.ModelSerializer):
	class Meta:
		model  = Driver
		fields = '__all__'

# ---------- Customer ----------

class CustomerAddressSerializer(serializers.ModelSerializer):
	class Meta:
		model	= CustomerAddress
		fields	= ('id', 'label', 'address', 'is_primary')



class CustomerSerializer(serializers.ModelSerializer):
	addresses	= CustomerAddressSerializer(many=True, required=False)

	class Meta:
		model	= Customer
		fields	= ('id', 'name', 'phone', 'memo', 'addresses')

	def _sync_addresses(self, instance, addresses):
		"""PUT 時は全置換して簡潔に"""
		instance.addresses.all().delete()
		for data in addresses:
			CustomerAddress.objects.create(customer=instance, **data)

	def create(self, validated_data):
		addresses	= validated_data.pop('addresses', [])
		customer	= super().create(validated_data)
		self._sync_addresses(customer, addresses)
		return customer

	def update(self, instance, validated_data):
		addresses = validated_data.pop('addresses', None)
		instance	= super().update(instance, validated_data)
		if addresses is not None:
			self._sync_addresses(instance, addresses)
		return instance





# ---------- 予約周り（ネスト用） ----------

class ReservationCastSerializer(serializers.ModelSerializer):
	stage_name = serializers.CharField(source='cast_profile.stage_name', read_only=True)
	avatar_url = serializers.SerializerMethodField()		# ★ CharField → 変更
	minutes	= serializers.IntegerField(source='course.minutes', read_only=True)

	course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())

	class Meta:
		model  = ReservationCast
		fields = '__all__'
		read_only_fields = ('reservation', 'rank_course')

	def get_avatar_url(self, obj):
		"""
		- cast_profile.photo_url は既に『絶対 or static』を返す property
		- request があれば必ず build_absolute_uri でフルパスに
		"""
		request = self.context.get('request')
		url = obj.cast_profile.photo_url or static('img/cast-default.png')
		return request.build_absolute_uri(url) if request else url


class ReservationChargeSerializer(serializers.ModelSerializer):
	option_name = serializers.CharField(source='option.name', read_only=True)

	class Meta:
		model  = ReservationCharge
		read_only_fields = ('reservation',)
		fields = '__all__'

class CashFlowSerializer(serializers.ModelSerializer):
	class Meta: model = CashFlow; fields = '__all__'


class ReservationDriverSerializer(serializers.ModelSerializer):
	driver_name = serializers.CharField(
		source="driver.user.display_name", read_only=True
	)

	class Meta:
		model  = ReservationDriver
		fields = (
			"id", "driver", "driver_name",
			"role", "start_at", "end_at",
			"collected_amount", "status",
		)
		read_only_fields = ("status",)

# ---------- 予約メイン ----------
class ReservationSerializer(serializers.ModelSerializer):
	courses = serializers.SerializerMethodField()
	options = serializers.SerializerMethodField()
	casts   = ReservationCastSerializer(many=True, required=False)
	charges = ReservationChargeSerializer(many=True, required=False)
	cast_photos = serializers.SerializerMethodField()
	store_name	  = serializers.CharField(source="store.name", read_only=True)
	customer_name   = serializers.CharField(source="customer.name", read_only=True)
	customer_address = serializers.CharField(source='customer.address', read_only=True)
	driver = serializers.PrimaryKeyRelatedField(
		queryset=Driver.objects.all(),
		allow_null=True,		  # ★これを追加
		required=False
	)
	drivers = ReservationDriverSerializer(many=True, required=False)
	driver_name	 = serializers.SerializerMethodField()
	cast_names	  = serializers.SerializerMethodField()
	course_minutes  = serializers.SerializerMethodField()
	expected_amount = serializers.IntegerField(read_only=True)
	address_book = serializers.PrimaryKeyRelatedField(
		queryset=CustomerAddress.objects.all(),
		allow_null=True, required=False
	)

	#送迎住所を１本化
	pickup_address = serializers.SerializerMethodField()

	class Meta:
		model  = Reservation
		fields = "__all__"
		read_only_fields = (
			"store_name", "customer_name", "driver_name",
			"cast_names", "course_minutes", "expected_amount","customer_address",
			"pickup_address",
		)

	def get_pickup_address(self, obj):
		"""
		① address_text（手書き）があれば優先
		② address_book があれば label + address
		"""
		if obj.address_text:
			return obj.address_text

		if obj.address_book_id:
			label = obj.address_book.label or ''
			addr  = obj.address_book.address
			return f"{label} / {addr}" if label else addr

		return ''

	def get_driver_name(self, obj):
		if not obj.driver_id:
			return ''
		user = obj.driver.user
		return user.display_name or user.username

	def get_cast_names(self, obj):
		return [c.cast_profile.stage_name for c in obj.casts.all()]

	def get_course_minutes(self, obj):
		"""
		先頭のキャストについて
		① ReservationCast.course が入っていればそれを優先
		② rank_course が入っていればそこから course.minutes
		③ どちらも無ければ '' を返して落ちないようにする
		"""
		first = obj.casts.first()
		if not first:
			return ''                       # キャスト自体が無い

		# ① course 直指定があればそれ
		if first.course_id:
			return first.course.minutes

		# ② rank_course 経由
		rc = first.rank_course
		if rc and rc.course_id:
			return rc.course.minutes

		# ③ どちらも無ければ空文字で回避
		return ''

	def get_courses(self, obj):
		return [
			{
				"cast":	  rc.cast_profile_id,
				"course_id": rc.course_id,
				"minutes":   rc.course.minutes,
			}
			for rc in obj.casts.all()
		]

	def get_options(self, obj):
		return [
			{
				"option_id": ch.option_id,
				"name":	  ch.option.name if ch.option else None,
				"amount":	ch.amount,
			}
			for ch in obj.charges.filter(kind="OPTION")
		]

	def get_cast_photos(self, obj):
		request = self.context.get("request")   # ← ここだけ追加
		urls = []
		for rc in obj.casts.all():
			u = rc.cast_profile.photo_url or static("img/cast-default.png")
			if request:						 # 絶対パス化
				u = request.build_absolute_uri(u)
			urls.append(u)
		return urls


	# ↓ 追加: 共通 NG 判定ヘルパ
	def _check_ng(self, customer, cast_profile_ids: list[int | CastProfile]):
		"""
		① キャスト側が顧客 NG
		② 顧客側がキャスト NG
		"""
		customer_id = customer.id if isinstance(customer, Customer) else customer

		# ★ オブジェクト → ID に統一
		cast_ids = [c.id if isinstance(c, CastProfile) else c for c in cast_profile_ids]

		qs = CastProfile.objects.filter(id__in=cast_ids)

		cust_ng_cast_ids = CastProfile.objects.filter(
			ng_customers__id=customer_id
		).values_list('id', flat=True)

		ng_casts = qs.filter(
			Q(ng_customers__id=customer_id) | Q(id__in=cust_ng_cast_ids)
		).distinct()

		if ng_casts.exists():
			names = ", ".join(c.stage_name for c in ng_casts)
			raise serializers.ValidationError(
				{"detail": f"NG設定により予約できません: {names}"}
			)



	def _check_option_ng(self, cast_profile_ids: list[int], option_ids: list[int]):
		if not option_ids:
			return
		ng = CastOption.objects.filter(
				cast_profile_id__in=cast_profile_ids,
				option_id__in=option_ids,
				is_enabled=False
			 ).select_related('cast_profile', 'option')
		if ng.exists():
			names = ", ".join(f"{o.cast_profile.stage_name}: {o.option.name}" for o in ng)
			raise serializers.ValidationError(
				{"detail": f"オプション NG: {names}"}
			)

	def _sync_charges(self, reservation, charges_data):
		ReservationCharge.objects.filter(reservation=reservation).delete()

		for ch in charges_data:
			ReservationCharge.objects.create(
				reservation	 = reservation,
				kind			= ch["kind"],
				# ★ オブジェクトを渡すように変更
				option		  = ch.get("option"),		  # ← ここ！
				extend_course   = ch.get("extend_course"),   # ← ここも同様
				amount		  = ch.get("amount"),
			)

	def _sync_casts(self, reservation, casts_data):
		ReservationCast.objects.filter(reservation=reservation).delete()
		for c in casts_data:
			# ★ ここを “*_id=” → “*=” に変えるだけで OK
			ReservationCast.objects.create(
				reservation   = reservation,
				cast_profile  = c["cast_profile"],   # ← オブジェクトをそのまま
				course		= c["course"],		 # ← 〃
				# rank_course は ReservationCast.save() 内で自動設定される
			)


	# --- ReservationSerializer の create() をまるっと差し替え ----------
	@transaction.atomic
	def create(self, validated_data):
		"""
		・drivers / casts / charges をネスト付きで受け取り
		・Reservation を作ったあとに個別に INSERT する
		（bulk_create だと model.save() が走らず rank_course 等が
			自動セットされないため）
		"""
		drivers_data = validated_data.pop("drivers", [])
		casts_data   = validated_data.pop("casts",   [])
		charges_data = validated_data.pop("charges", [])

		# ① NG 系バリデーション（必要なら↓を有効に）
		# self._check_ng(
		#	 validated_data.get("customer"),
		#	 [c["cast_profile"] for c in casts_data],
		# )
		# self._check_option_ng(
		#	 [c["cast_profile"] for c in casts_data],
		#	 [ch["option"] for ch in charges_data if ch["kind"] == "OPTION"],
		# )

		# ② 親テーブル
		reservation = super().create(validated_data)

		# ③ 子テーブルは save() を通して 1 件ずつ作る
		for d in drivers_data:
			ReservationDriver.objects.create(reservation=reservation, **d)

		for c in casts_data:
			# ReservationCast.save() 内で rank_course などを解決させるため
			ReservationCast.objects.create(reservation=reservation, **c)

		for ch in charges_data:
			ReservationCharge.objects.create(reservation=reservation, **ch)

		return reservation

	# ------- 更新 --------
	def update(self, instance, validated_data):
		# ① ネストを抜き取っておく
		casts_data   = validated_data.pop('casts',   None)
		drivers_data = validated_data.pop('drivers', None)
		charges_data = validated_data.pop('charges', None)

		# ② 親モデルを更新
		for attr, value in validated_data.items():
			setattr(instance, attr, value)
		instance.save()

		# ③ ネストは好きなロジックで同期（例: 全削除→再作成）
		if casts_data is not None:
			instance.casts.all().delete()
			for c in casts_data:
				ReservationCast.objects.create(reservation=instance, **c)

		if drivers_data is not None:
			instance.drivers.all().delete()			   # ← related_name に合わせる
			for d in drivers_data:
				ReservationDriver.objects.create(
					reservation = instance,
					**d		 # kind, driver など
				)

		if charges_data is not None:
			instance.charges.all().delete()
			for ch in charges_data:
				ReservationCharge.objects.create(reservation=instance, **ch)

		return instance

	def get_courses(self, obj):
		rows = []
		for rc in obj.casts.all():
			course = rc.course or getattr(rc.rank_course, "course", None)
			if not course:
				# ログに残すだけでスキップ
				import logging
				logging.warning(f"ReservationCast {rc.id} has no course")
				continue
			rows.append({
				"cast":	  rc.cast_profile_id,
				"course_id": course.id,
				"minutes":   course.minutes,
			})
		return rows

	def get_cast_names(self, obj):
		"""
		DB ベンダに依存しないキャスト名一覧（重複除去＋順序保証）
		"""
		names = {c.cast_profile.stage_name for c in obj.casts.all()}
		return sorted(names)


class CustomerReservationSerializer(ReservationSerializer):
	courses = serializers.SerializerMethodField()
	options = serializers.SerializerMethodField()

	class Meta(ReservationSerializer.Meta):
		fields = '__all__'

	# ───── ここが肝心 ──────────────────
	def get_courses(self, obj):
		return [
			{
				"cast":	  rc.cast_profile_id,
				"course_id": rc.course_id,
				"minutes":   rc.course.minutes,
			}
			for rc in obj.casts.all()
		]

	def get_options(self, obj):
		return [
			{
				"option_id": ch.option_id,
				"name":	  ch.option.name if ch.option else None,
				"amount":	ch.amount,
			}
			for ch in obj.charges.filter(kind="OPTION")
		]



# ---------- ユーザー ----------
User = get_user_model() 

class UserDetailSerializer(serializers.ModelSerializer):
	"""
	全ユーザー情報で共通して使うシリアライザー
	- dj_rest_auth の /user/ エンドポイント
	- DriverListSerializer などのネスト先
	"""
	groups	  = serializers.SlugRelatedField(
		many=True, read_only=True, slug_field='name'
	)
	avatar_url  = serializers.SerializerMethodField()

	class Meta(UserDetailsSerializer.Meta):
		model  = User
		# UserDetailsSerializer.Meta.fields = ('pk','username','email',...) なので
		# それに追加したい項目を全部並べる
		fields = UserDetailsSerializer.Meta.fields + (
			'display_name',
			'groups',
			'avatar_url',
		)

	def get_avatar_url(self, obj):
		request = self.context.get("request")
		url = obj.avatar.url if obj.avatar else static("img/user-default.png")
		return request.build_absolute_uri(url) if request else url




class ShiftPlanSerializer(serializers.ModelSerializer):
	stage_name = serializers.CharField(source='cast_profile.stage_name')
	store_name = serializers.CharField(source='cast_profile.store.name')
	photo_url  = serializers.CharField(source='cast_profile.photo_url', read_only=True)  # ★追加

	is_checked_in = serializers.BooleanField(read_only=True)

	class Meta:
		model  = ShiftPlan
		fields = [
			'id', 'store', 'store_name', 'cast_profile',
			'date',
			'stage_name', 'photo_url',
			'start_at', 'end_at', 'is_checked_in',
		]
class ShiftAttendanceSerializer(serializers.ModelSerializer):
	class Meta:
		model  = ShiftAttendance
		fields = "__all__"
		read_only_fields = ("checked_in_at", "checked_out_at")



