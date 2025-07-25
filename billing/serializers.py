# billing/serializer.py
from rest_framework import serializers
from .models import Store, Table, Bill, ItemMaster, BillItem, CastPayout, BillCastStay, Cast, ItemCategory
from django.utils import timezone
from dj_rest_auth.serializers import UserDetailsSerializer
from .models import User
from cloudinary.utils import cloudinary_url
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string


class StoreSerializer(serializers.ModelSerializer):
	class Meta:
		model	= Store
		fields	= '__all__'


class TableSerializer(serializers.ModelSerializer):
	class Meta:
		model	= Table
		fields	= '__all__'


class CastPayoutSerializer(serializers.ModelSerializer):
	class Meta:
		model	= CastPayout
		fields	= '__all__'


class ItemMasterSerializer(serializers.ModelSerializer):
	# ------ READ ------
	# フロント互換: 'drink' / 'setVip' … をそのまま返す
	category = serializers.CharField(source='category.code', read_only=True)

	# ------ WRITE -----
	# POST / PUT では `category_id` に FK を渡す
	category_id = serializers.PrimaryKeyRelatedField(
		source='category',
		queryset=ItemCategory.objects.all(),
		write_only=True,
	)

	class Meta:						 # ★←欠けていた
		model  = ItemMaster
		fields = [
			'id', 'name', 'code', 'price_regular',
			'duration_min', 'apply_service',
			'exclude_from_payout', 'track_stock',
			# ↓ 上で定義した 2 つを必ず含める
			'category', 'category_id',
		]



class TableMiniSerializer(serializers.ModelSerializer):
	store = serializers.IntegerField(source='store.id', read_only=True)   # ★追加
	class Meta:
		model  = Table
		fields = ('id', 'number', 'store')

class BillCastStayMini(serializers.ModelSerializer):
	class Meta:
		model  = BillCastStay
		fields = ('cast',)		   # cast は {id, stage_name} で返る



class CastMiniSerializer(serializers.ModelSerializer):
	avatar_url = serializers.SerializerMethodField()
	class Meta:
		model  = Cast
		fields = ("id", "stage_name", "avatar_url")

	def get_avatar_url(self, obj):
		if obj.avatar:
			return cloudinary_url(
				obj.avatar.public_id,
				format=obj.avatar.format,
				secure=True	 # https:// 付与
			)[0]
		return None


class BillItemSerializer(serializers.ModelSerializer):
	# --------------------<<  WRITE 用  >>--------------------
	# 送信時は ID だけ受け取るフィールド
	served_by_cast_id = serializers.PrimaryKeyRelatedField(
		source='served_by_cast',			 # ← Model フィールド名
		queryset=Cast.objects.all(),
		write_only=True,					 # ← 書き込み専用
		required=False,
		allow_null=True,	# ← null を許容
	)
	code = serializers.CharField(
		source='item_master.code',			# ← ★追加
		read_only=True)
	duration_min  = serializers.IntegerField(
		source='item_master.duration_min',	# ← ★追加（あれば便利）
		read_only=True)	

	# --------------------<<  READ 用  >>---------------------
	# 取得時はミニキャストオブジェクトを返す
	served_by_cast = CastMiniSerializer(read_only=True)
	# 小計はサーバ側で算出するだけ
	subtotal = serializers.SerializerMethodField()
	bill = serializers.PrimaryKeyRelatedField(read_only=True)

	class Meta:
		model  = BillItem
		fields = '__all__'
		read_only_fields = ('bill', 'subtotal')

	def get_subtotal(self, obj):
		return obj.subtotal


User = get_user_model()

class CastSerializer(serializers.ModelSerializer):
	# ---------- 店が入力・更新できる write‑only フィールド ----------
	username	= serializers.CharField(write_only=True, required=True)
	first_name  = serializers.CharField(write_only=True, required=False, allow_blank=True)
	last_name   = serializers.CharField(write_only=True, required=False, allow_blank=True)

	# ---------- 取得時に返す read‑only フィールド ----------
	username_read   = serializers.CharField(source='user.username',   read_only=True)
	first_name_read = serializers.CharField(source='user.first_name', read_only=True)
	last_name_read  = serializers.CharField(source='user.last_name',  read_only=True)

	avatar_url = serializers.SerializerMethodField()

	store = serializers.PrimaryKeyRelatedField(
		queryset=Store.objects.all(),
		required=False, write_only=True,
	)

	class Meta:
		model  = Cast
		fields = (
			"id", "stage_name", "store",
			# ← ここから User 関連
			"username", "username_read",
			"first_name", "first_name_read",
			"last_name",  "last_name_read",
			# ← バック率
			"back_rate_free_override",
			"back_rate_nomination_override",
			"back_rate_inhouse_override",
			# ← 画像
			"avatar", "avatar_url",
		)

	# ---------- helper ----------
	def get_avatar_url(self, obj):
		if obj.avatar:
			return cloudinary_url(obj.avatar.public_id,
								  format=obj.avatar.format,
								  secure=True)[0]
		return None

	# ---------- CREATE ----------
	def create(self, validated):
		username   = validated.pop("username")
		first_name = validated.pop("first_name", "")
		last_name  = validated.pop("last_name", "")

		# ---------- 店舗を request.user から補完 ----------
		request = self.context.get("request")
		if not validated.get("store") and request and hasattr(request.user, "store_profile"):
			validated["store"] = request.user.store_profile.store

		user = User.objects.create_user(
			username=username,
			password=get_random_string(12),
			first_name=first_name,
			last_name=last_name,
		)
		return Cast.objects.create(user=user, **validated)

	# ---------- UPDATE ----------
	def update(self, instance, validated):
		user = instance.user
		# username / first_name / last_name が来ていたら更新
		if "username"   in validated: user.username   = validated.pop("username")
		if "first_name" in validated: user.first_name = validated.pop("first_name")
		if "last_name"  in validated: user.last_name  = validated.pop("last_name")
		user.save(update_fields=["username", "first_name", "last_name"])
		return super().update(instance, validated)


	def to_representation(self, obj):
		data = super().to_representation(obj)
		# 既定バック率（店舗共通）を ItemCategory から取得
		cat = ItemCategory.objects.get(code="drink")
		data["back_rate_free_override"] = (
			obj.back_rate_free_override
			if obj.back_rate_free_override is not None else cat.back_rate_free
		)
		data["back_rate_nomination_override"] = (
			obj.back_rate_nomination_override
			if obj.back_rate_nomination_override is not None else cat.back_rate_nomination
		)
		data["back_rate_inhouse_override"] = (
			obj.back_rate_inhouse_override
			if obj.back_rate_inhouse_override is not None else cat.back_rate_inhouse
		)
		return data

class BillCastStaySerializer(serializers.ModelSerializer):
	cast = CastMiniSerializer()				   # ← ネストに置き換え

	class Meta:
		model  = BillCastStay
		fields = ("cast", "entered_at", "left_at", "stay_type")


class BillSerializer(serializers.ModelSerializer):
	# ---------- READ ----------
	table		= TableMiniSerializer(read_only=True)	 # ネスト表示用
	items		= BillItemSerializer(read_only=True, many=True)
	stays		= BillCastStaySerializer(read_only=True, many=True)
	subtotal	 = serializers.SerializerMethodField()
	service_charge = serializers.SerializerMethodField()
	tax		  = serializers.SerializerMethodField()
	grand_total  = serializers.SerializerMethodField()
	inhouse_casts = CastSerializer(many=True, read_only=True)
	expected_out = serializers.DateTimeField(read_only=True)
	set_rounds   = serializers.IntegerField(read_only=True)
	ext_minutes  = serializers.IntegerField(read_only=True)
	# ---------- WRITE ----------
	# “卓番号” を受け取る専用フィールド
	table_id = serializers.PrimaryKeyRelatedField(
		source='table',				# ← Bill.table へマッピング
		queryset=Table.objects.all(),
		allow_null=True,
		required=False,
		write_only=True,
	)

	free_ids = serializers.PrimaryKeyRelatedField(
		many=True,
		queryset=Cast.objects.all(),
		required=False,
		write_only=True,
	)

   # ★ これを“トップレベル”で宣言し直す
	inhouse_casts_w   = serializers.PrimaryKeyRelatedField(
		many=True, queryset=Cast.objects.all(),
		required=False, write_only=True
	)

	nominated_casts = serializers.PrimaryKeyRelatedField(
		many=True, queryset=Cast.objects.all(), required=False
	)

	class Meta:
		model = Bill
		fields = (
			# ---- 基本 ----
			"id", "table", "table_id", "opened_at", "closed_at",
			# ---- 金額 ----
			"subtotal", "service_charge", "tax", "grand_total", "total",
			# ---- 関連 ----
			"items", "stays","expected_out",
			"nominated_casts", "settled_total",
			"inhouse_casts",		# READ
			"inhouse_casts_w",	  # WRITE
			"free_ids","set_rounds","ext_minutes",
		)
		read_only_fields = (
			"subtotal", "service_charge", "tax", "grand_total", "total",
			"opened_at", "closed_at", "settled_total","expected_out","set_rounds","ext_minutes",
		)
		depth = 2

	# ───────── READ helpers ──────────
	def get_inhouse_casts(self, obj):
		return list(
			obj.stays.filter(stay_type="in")
			   .values_list("cast_id", flat=True)
		)

	# --------------------------------------------------
	#				 CREATE
	# --------------------------------------------------
	def create(self, validated_data):
		nominated = validated_data.pop("nominated_casts", [])
		bill = Bill.objects.create(**validated_data)   # table もここでセットされる
		if nominated:
			bill.nominated_casts.set(nominated)
		return bill

	# --------------------------------------------------
	#				 UPDATE
	# --------------------------------------------------
	# billing/serializers.py  ── BillSerializer.update


	def update(self, instance, validated_data):
		"""
		本指名・場内・フリーをまとめて更新する。
		・再入店は新しい stay 行を追加。
		・退席は left_at を付与して履歴を残す。
		"""
		# ---------- 1. 送信された ID 群を取り出す ----------
		nominated_raw = validated_data.pop("nominated_casts", None)
		inhouse_raw   = validated_data.pop("inhouse_casts_w", None)
		free_raw      = validated_data.pop("free_ids", None)

		to_ids = lambda raw: [
			c.id if isinstance(c, Cast) else c for c in (raw or [])
		]
		nominated_ids = to_ids(nominated_raw)
		inhouse_ids   = to_ids(inhouse_raw)
		free_ids_orig = to_ids(free_raw)

		# ---------- 2. 通常フィールドを更新 ----------
		instance = super().update(instance, validated_data)

		# ---------- 3. 既存 stay をキャッシュ ----------
		stay_map = {s.cast_id: s for s in instance.stays.all()}

		# ===============================================================
		#  A. 本指名 (nom)
		# ===============================================================
		if nominated_raw is not None:
			instance.nominated_casts.set(nominated_ids)
			for cid in nominated_ids:
				stay = stay_map.get(cid)
				if not stay:
					BillCastStay.objects.create(
						bill=instance, cast_id=cid,
						entered_at=timezone.now(), stay_type="nom"
					)
				elif stay.stay_type != "nom":
					stay.stay_type = "nom"
					stay.left_at   = None
					stay.save(update_fields=["stay_type", "left_at"])
			for cid, stay in stay_map.items():
				if cid not in nominated_ids and stay.stay_type == "nom":
					stay.stay_type = "in" if cid in inhouse_ids else "free"
					stay.save(update_fields=["stay_type"])

		# ===============================================================
		#  B. 場内 (in)
		# ===============================================================
		if inhouse_raw is not None:
			for cid in inhouse_ids:
				stay = stay_map.get(cid)
				if not stay:
					BillCastStay.objects.create(
						bill=instance, cast_id=cid,
						entered_at=timezone.now(), stay_type="in"
					)
				else:
					stay.stay_type = "in"
					stay.left_at   = None
					stay.save(update_fields=["stay_type", "left_at"])
			for cid, stay in stay_map.items():
				if cid not in inhouse_ids and stay.stay_type == "in":
					stay.stay_type = "free"
					stay.save(update_fields=["stay_type"])

		# ===============================================================
		#  C. フリー (free)
		# ===============================================================
		if free_raw is not None:
			# ① in / nom に含まれる ID を除外して「純粋な free のみ」にする
			free_ids = [
				cid for cid in free_ids_orig
				if cid not in inhouse_ids and cid not in nominated_ids
			]

			# ② free_ids を在席状態に
			for cid in free_ids:
				stay = stay_map.get(cid)
				if not stay:
					BillCastStay.objects.create(
						bill=instance, cast_id=cid,
						entered_at=timezone.now(), stay_type="free"
					)
				else:
					if stay.left_at:
						BillCastStay.objects.create(
							bill=instance, cast_id=cid,
							entered_at=timezone.now(), stay_type="free"
						)
					elif stay.stay_type != "free":
						stay.stay_type = "free"
						stay.save(update_fields=["stay_type"])

			# ③ free から外れた人 → 退席
			active_free = instance.stays.filter(
				stay_type="free", left_at__isnull=True
			)
			for stay in active_free:
				if stay.cast_id not in free_ids:
					stay.left_at = timezone.now()
					stay.save(update_fields=["left_at"])

		# ===============================================================
		return instance



	# ── 共通計算ロジック ─────────────────
	def _store_rates(self, obj):
		if not obj.table_id:
			return Decimal("0"), Decimal("0")
		store = obj.table.store
		sr = Decimal(store.service_rate)
		tr = Decimal(store.tax_rate)
		sr = sr / 100 if sr >= 1 else sr
		tr = tr / 100 if tr >= 1 else tr
		return sr, tr

	def get_subtotal(self, obj):
		return sum(i.subtotal for i in obj.items.all())

	def get_service_charge(self, obj):
		subtotal, (sr, _) = self.get_subtotal(obj), self._store_rates(obj)
		return round(subtotal * sr)

	def get_tax(self, obj):
		subtotal = self.get_subtotal(obj)
		svc	  = self.get_service_charge(obj)
		_, tr	= self._store_rates(obj)
		return round((subtotal + svc) * tr)

	def get_grand_total(self, obj):
		return obj.total or (
			self.get_subtotal(obj) +
			self.get_service_charge(obj) +
			self.get_tax(obj)
		)
