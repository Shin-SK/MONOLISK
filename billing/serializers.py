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

class BillItemSerializer(serializers.ModelSerializer):
	bill = serializers.PrimaryKeyRelatedField(read_only=True)
	payouts = CastPayoutSerializer(read_only=True, many=True)
	subtotal = serializers.SerializerMethodField()
	served_by_cast_name = serializers.CharField(
		source='served_by_cast.stage_name',
		read_only=True
	)
	class Meta:
		model  = BillItem
		fields = '__all__'

	def get_subtotal(self, obj):
		return obj.price * obj.qty


class CastSerializer(serializers.ModelSerializer):
	avatar_url = serializers.SerializerMethodField()

	class Meta:
		model  = Cast
		fields = ("id", "stage_name", "store",
				  "avatar",
				  "avatar_url")

	def get_avatar_url(self, obj):
		return obj.avatar.url if obj.avatar else None


class CastMiniSerializer(serializers.ModelSerializer):
	avatar_url = serializers.SerializerMethodField()
	class Meta:
		model  = Cast
		fields = ("id", "stage_name", "avatar_url")

	def get_avatar_url(self, obj):
		# CloudinaryField/FileField は .url でフル URL が取れる
		return obj.avatar.url if obj.avatar else None


class BillCastStaySerializer(serializers.ModelSerializer):
	cast = CastMiniSerializer()				   # ← ネストに置き換え

	class Meta:
		model  = BillCastStay
		fields = ("cast", "entered_at", "left_at", "stay_type")

# serializers.py ------------------------
class BillSerializer(serializers.ModelSerializer):
	table  = TableMiniSerializer(read_only=True)
	items  = BillItemSerializer(read_only=True, many=True)
	stays = BillCastStaySerializer(many=True)
	total  = serializers.IntegerField(read_only=True)
	nominated_casts = serializers.PrimaryKeyRelatedField(
		many=True, queryset=Cast.objects.all()
	)
	# READ
	inhouse_casts = serializers.SerializerMethodField()
	def get_inhouse_casts(self, obj):
		return list(obj.stays.filter(stay_type='in').values_list('cast_id', flat=True))

	# WRITE
	inhouse_casts = serializers.SerializerMethodField()
	inhouse_casts_w = serializers.PrimaryKeyRelatedField(		# ★別名
		many=True, queryset=Cast.objects.all(), write_only=True, required=False
	)

	# ─ 追加フィールド ──────────────────
	subtotal	   = serializers.SerializerMethodField()
	service_charge = serializers.SerializerMethodField()
	tax			= serializers.SerializerMethodField()
	grand_total	= serializers.SerializerMethodField()

	class Meta:
		model  = Bill
		fields = (
			'id', 'table', 'opened_at', 'closed_at',
			'subtotal', 'service_charge', 'tax', 'grand_total',
			'total',
			'items', 'stays',
			'nominated_casts',
			'inhouse_casts',	 # ← READ
			'inhouse_casts_w',   # ← ★ WRITE も忘れず列挙
		)
		depth = 2

	def update(self, instance, validated_data):
		nominated_ids = validated_data.pop('nominated_casts',  None)
		inhouse_objs  = validated_data.pop('inhouse_casts_w', None)   # ← Cast の list
		inhouse_ids   = [c.id if isinstance(c, Cast) else c		  # ★PK の list に変換
						 for c in (inhouse_objs or [])]

		# ---------- 通常フィールド ----------
		for k, v in validated_data.items():
			setattr(instance, k, v)
		instance.save()

		# ---------- nominated ----------
		if nominated_ids is not None:
			instance.nominated_casts.set(nominated_ids)

		# ---------- inhouse ----------
		if inhouse_objs is not None:		  # None＝キーが無かった時はスキップ
			stay_map = {s.cast_id: s for s in instance.stays.all()}

			# ① 指定キャストを in に／新規 stay も作成
			for cid in inhouse_ids:
				stay = stay_map.get(cid)
				if stay:
					if stay.stay_type != 'in':
						stay.stay_type = 'in'
						stay.save()
				else:
					BillCastStay.objects.create(
						bill	   = instance,
						cast_id	= cid,
						entered_at = timezone.now(),
						stay_type  = 'in',
					)

			# ② それ以外の in→free へ戻す
			for cid, stay in stay_map.items():
				if cid not in inhouse_ids and stay.stay_type == 'in':
					stay.stay_type = 'free'
					stay.save()

		return instance

	def get_items(self, obj):
		# 既存ロジックそのまま
		return BillItemSerializer(obj.items.all(), many=True).data

	# ── 共通計算ロジック ─────────────────
	def _store_rates(self, obj):
		store = obj.table.store
		sr = Decimal(store.service_rate)
		tr = Decimal(store.tax_rate)
		# 1 以上なら “％” 扱いにして ÷100
		sr = sr / 100 if sr >= 1 else sr
		tr = tr / 100 if tr >= 1 else tr
		return sr, tr

	def get_subtotal(self, obj):
		return sum(i.subtotal for i in obj.items.all())

	def get_service_charge(self, obj):
		subtotal = self.get_subtotal(obj)
		sr, _ = self._store_rates(obj)
		return round(subtotal * sr)

	def get_tax(self, obj):
		subtotal		  = self.get_subtotal(obj)
		service_charge	= self.get_service_charge(obj)
		_, tr			 = self._store_rates(obj)
		return round((subtotal + service_charge) * tr)

	def get_grand_total(self, obj):
		# Bill が「締め済み」なら確定値を優先
		if obj.total:
			return obj.total
		return (
			self.get_subtotal(obj)
			+ self.get_service_charge(obj)
			+ self.get_tax(obj)
		)