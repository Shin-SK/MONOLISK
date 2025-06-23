#serializers.py
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from rest_framework import serializers
from dj_rest_auth.serializers import UserDetailsSerializer
from django.db.models import Q
from .models import (
	Store, Rank, Course, RankCourse, Option, GroupOptionPrice,
	CastProfile, CastCoursePrice, CastOption, Driver, Customer,
	Reservation, ReservationCast, ReservationCharge, CashFlow
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
class CustomerSerializer(serializers.ModelSerializer):
	class Meta: model = Customer; fields = '__all__'

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

# ---------- 予約メイン ----------
class ReservationSerializer(serializers.ModelSerializer):
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
	driver_name	 = serializers.SerializerMethodField()
	cast_names	  = serializers.SerializerMethodField()
	course_minutes  = serializers.SerializerMethodField()
	expected_amount = serializers.IntegerField(read_only=True)

	class Meta:
		model  = Reservation
		fields = "__all__"
		read_only_fields = (
			"store_name", "customer_name", "driver_name",
			"cast_names", "course_minutes", "expected_amount","customer_address",
		)

	def get_driver_name(self, obj):
		if not obj.driver_id:
			return ''
		user = obj.driver.user
		return user.display_name or user.username

	def get_cast_names(self, obj):
		return [c.cast_profile.stage_name for c in obj.casts.all()]

	def get_course_minutes(self, obj):
		first = obj.casts.first()
		return first.rank_course.course.minutes if first else ''


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
		"""
		charges 配列で ReservationCharge 行を置き換える
		"""
		ReservationCharge.objects.filter(reservation=reservation).delete()
		objs = [
			ReservationCharge(
				reservation = reservation,
				kind		= c["kind"],
				option_id   = c.get("option"),
				extend_course_id = c.get("extend_course"),
				amount	  = c.get("amount"),
			) for c in charges_data
		]
		ReservationCharge.objects.bulk_create(objs)

	def _sync_casts(self, reservation, casts_data):
		ReservationCast.objects.filter(reservation=reservation).delete()
		for c in casts_data:
			ReservationCast.objects.create(
				reservation      = reservation,
				cast_profile_id  = c["cast_profile"],
				course_id        = c["course"],        # rank_course 渡さない
			)



	# ------- 新規 --------
	def create(self, validated_data):
		casts_data = validated_data.pop("casts", [])
		charges	= validated_data.pop("charges", [])

		# NG 判定
		self._check_ng(
			validated_data.get("customer"),
			[c["cast_profile"] for c in casts_data]
		)
		self._check_option_ng(
			[c["cast_profile"] for c in casts_data],
			[ch["option"] for ch in charges if ch["kind"] == "OPTION"]
		)

		reservation = super().create(validated_data)
		self._sync_casts(reservation, casts_data)
		self._sync_charges(reservation, charges)
		return reservation

	# ------- 更新 --------
	def update(self, instance, validated_data):
		# pop のデフォルトを None に
		casts_data   = validated_data.pop('casts',   None)
		charges_data = validated_data.pop('charges', None)

		# 現在の cast_ids をまず決定
		cast_ids = (
			[c['cast_profile'] for c in casts_data] if casts_data is not None
			else list(instance.casts.values_list('cast_profile_id', flat=True))
		)

		# NG 判定
		self._check_ng(
			validated_data.get('customer', instance.customer_id),
			cast_ids
		)
		if charges_data is not None:
			self._check_option_ng(
				cast_ids,
				[c['option'] for c in charges_data if c['kind'] == 'OPTION']
			)

		# モデル保存（received_amount だけなら本当にそこだけ更新）
		reservation = super().update(instance, validated_data)

		if casts_data is not None:
			self._sync_casts(reservation, casts_data)
		if charges_data is not None:
			self._sync_charges(reservation, charges_data)

		return reservation



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