# billing/serializer.py
from rest_framework import serializers
from .models import Store, Table, Bill, ItemMaster, BillItem, CastPayout, BillCastStay, Cast
from django.utils import timezone
from dj_rest_auth.serializers import UserDetailsSerializer
from .models import User
from decimal import Decimal, ROUND_HALF_UP


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
	class Meta:
		model	= ItemMaster
		fields = [
			'id', 'name', 'code', 'price_regular',  # ← code を含める
			'category', 'duration_min',
			'apply_service', 'exclude_from_payout', 'track_stock',
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
		# CloudinaryField/FileField は .url でフル URL が取れる
		return obj.avatar.url if obj.avatar else None


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



class CastSerializer(serializers.ModelSerializer):
	avatar_url = serializers.SerializerMethodField()

	class Meta:
		model  = Cast
		fields = ("id", "stage_name", "store",
				  "avatar",
				  "avatar_url")

	def get_avatar_url(self, obj):
		return obj.avatar.url if obj.avatar else None




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
			"items", "stays",
			"nominated_casts", "settled_total",
			"inhouse_casts",		# READ
			"inhouse_casts_w",	  # WRITE
			"free_ids",
		)
		read_only_fields = (
			"subtotal", "service_charge", "tax", "grand_total", "total",
			"opened_at", "closed_at", "settled_total",
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
	# billing/serializers.py  ── BillSerializer.update 内
	def update(self, instance, validated_data):
		nominated_raw = validated_data.pop("nominated_casts", None)
		inhouse_raw   = validated_data.pop("inhouse_casts_w", None)

		nominated_ids = [c.id if isinstance(c, Cast) else c
						for c in (nominated_raw or [])]
		inhouse_ids   = [c.id if isinstance(c, Cast) else c
						for c in (inhouse_raw or [])]

		# 通常フィールド
		instance = super().update(instance, validated_data)

		# ――― 共通で使う stay マップを先に作っておく ―――
		stay_map = {s.cast_id: s for s in instance.stays.all()}

		# ---------- 本指名 ----------
		if nominated_raw is not None:
			instance.nominated_casts.set(nominated_ids)

			# ① nominated 全員を stay_type='nom' に upsert
			for cid in nominated_ids:
				stay, created = BillCastStay.objects.get_or_create(
					bill=instance, cast_id=cid,
					defaults={"entered_at": timezone.now(), "stay_type": "nom"},
				)
				if not created and stay.stay_type != "nom":
					stay.stay_type = "nom"; stay.save()

			# ② もう nominated でなくなった人は free（ただし in が優先）
			for cid, stay in stay_map.items():
				if cid not in nominated_ids and stay.stay_type == "nom":
					# inhouse ならそのまま、そうでなければ free
					if cid not in inhouse_ids:
						stay.stay_type = "free"; stay.save()

		# ---------- 場内 ----------
		if inhouse_raw is not None:
			# ① 指定キャストを in に
			for cid in inhouse_ids:
				stay = stay_map.get(cid)
				if stay and stay.stay_type != "in":
					stay.stay_type = "in"; stay.save()
				elif not stay:
					BillCastStay.objects.create(
						bill=instance, cast_id=cid,
						entered_at=timezone.now(), stay_type="in"
					)

			# ② inhouse から外れた人 → free
			for cid, stay in stay_map.items():
				if cid not in inhouse_ids and stay.stay_type == "in":
					stay.stay_type = "free"; stay.save()

		# ---------- FREE ----------
		free_raw = validated_data.pop("free_ids", None)
		if free_raw is not None:
			free_ids = [
				c.id if isinstance(c, Cast) else c
				for c in free_raw
			]
			# ① free_ids の upsert
			for cid in free_ids:
				BillCastStay.objects.get_or_create(
					bill=instance, cast_id=cid,
					defaults={
						"entered_at": timezone.now(),
						"stay_type": "free",
					},
				)
			# ② free から外れた人は削除 or 状態変更
			for cid, stay in stay_map.items():
				if cid not in free_ids and stay.stay_type == "free":
					stay.delete()

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
