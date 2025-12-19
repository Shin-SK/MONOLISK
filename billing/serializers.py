# billing/serializer.py
from rest_framework import serializers
from .models import Store, Table, Bill, ItemMaster, BillItem, CastPayout, BillCastStay, Cast, ItemCategory, CastCategoryRate, CastShift, CastDailySummary, Staff, StaffShift, Customer, CustomerLog, StoreSeatSetting, SeatType, DiscountRule, CastGoal, User, CustomerTag
from dj_rest_auth.serializers import UserDetailsSerializer
from cloudinary.utils import cloudinary_url
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from datetime import date
from .services import sync_nomination_fees
from django.templatetags.static import static
from django.utils import timezone
from .models_profile import get_user_avatar_url
from django.db import transaction
from django.db.models import Sum

from .models import Bill, BillDiscountLine
from billing.constants import (
    BILLITEM_QTY_MIN, BILLITEM_QTY_MAX,
    BILLITEM_PRICE_MIN, BILLITEM_PRICE_MAX,
    BILL_PAYMENT_MIN, BILL_PAYMENT_MAX, BILL_OVERPAY_TOLERANCE,
    ERROR_MESSAGES
)



class StoreSerializer(serializers.ModelSerializer):
    business_hours_display = serializers.CharField(read_only=True)
    
    class Meta:
        model    = Store
        fields    = '__all__'


class TableSerializer(serializers.ModelSerializer):
    number = serializers.SerializerMethodField()
    seat_type_code = serializers.SerializerMethodField()
    seat_type_name = serializers.SerializerMethodField()

    def get_number(self, obj): return getattr(obj, 'code', '') or ''
    def get_seat_type_code(self, obj):
        st = getattr(obj, 'seat_type', None)
        return getattr(st, 'code', None)
    def get_seat_type_name(self, obj):
        st = getattr(obj, 'seat_type', None)
        return getattr(st, 'name', None)

    class Meta:
        model  = Table
        fields = ('id','code','number','seat_type','seat_type_code','seat_type_name')


class StoreSeatSettingSerializer(serializers.ModelSerializer):
    seat_type_display = serializers.CharField(source='seat_type.name', read_only=True)
    seat_type_code    = serializers.CharField(source='seat_type.code', read_only=True)

    class Meta:
        model = StoreSeatSetting
        fields = [
            'id', 'store', 'seat_type', 'seat_type_code', 'seat_type_display',
            'service_rate', 'charge_per_person',
            'extension_30_price', 'free_time_price', 'private_price',
            'memo',
        ]
        read_only_fields = ['id']

class CastPayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model    = CastPayout
        fields    = '__all__'
  
class CastSalesSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Cast
        fields = (
            'id', 'stage_name',
            'sales_champ', 'sales_nom', 'sales_in', 'sales_free',
            'total', 'payroll',
        )

class BillItemMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BillItem
        fields = ['id', 'name', 'qty', 'price', 'is_nomination',
                  'is_inhouse', 'exclude_from_payout']


class BillMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Bill
        fields = ['id', 'opened_at', 'closed_at', 
                  'grand_total','subtotal','table', 'expected_out',
                  'table', 'memo']


class TableMiniSerializer(serializers.ModelSerializer):
    store = serializers.IntegerField(source='store.id', read_only=True)
    number = serializers.SerializerMethodField()  # 互換：旧 number を復活（中身は code）
    seat_type_name = serializers.SerializerMethodField()
    seat_type_code = serializers.SerializerMethodField()
    def get_number(self, obj):
        return getattr(obj, 'code', '') or ''   # undefined回避

    def get_seat_type_code(self, obj):
        st = getattr(obj, 'seat_type', None)
        return getattr(st, 'code', None)

    def get_seat_type_name(self, obj):
        st = getattr(obj, 'seat_type', None)
        return getattr(st, 'name', None)

    class Meta:
        model  = Table
        fields = ('id','number','code','store','seat_type',
                  'seat_type_code','seat_type_name')



class CastItemDetailSerializer(serializers.ModelSerializer):
    bill_id    = serializers.IntegerField(source='bill.id', read_only=True)
    closed_at  = serializers.DateTimeField(source='bill.closed_at', read_only=True)
    table_no   = serializers.SerializerMethodField()
    subtotal   = serializers.SerializerMethodField()
    back_rate  = serializers.SerializerMethodField()
    amount     = serializers.SerializerMethodField()
    category   = serializers.SerializerMethodField()

    class Meta:
        model  = BillItem
        fields = (
            'id', 'closed_at', 'bill_id', 'table_no',
            'name', 'qty', 'subtotal', 'back_rate', 'amount',
            'is_nomination', 'is_inhouse',
            'category',
        )

    def get_subtotal(self, obj): return obj.subtotal
    def get_back_rate(self, obj): return float(obj.back_rate)
    def get_amount(self, obj):
        return int(obj.subtotal * obj.back_rate)
    def get_category(self, obj):
        c = getattr(getattr(obj, 'item_master', None), 'category', None)
        if not c: return None
        return {'code': c.code, 'name': c.name, 'show_in_menu': c.show_in_menu}
    def get_table_no(self, obj):
        tbl = getattr(getattr(obj, 'bill', None), 'table', None)
        return (getattr(tbl, 'code', '') or '') if tbl else ''

class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = ItemCategory
        fields = ("code", "name")     # これだけで OK


class ItemCategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ItemCategory
        fields = ('code', 'name', 'show_in_menu')



class ItemMasterSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()   # ★ここを変更

    def get_category(self, obj):
        return {
            "code": obj.category.code,
            "name": obj.category.name, 
            "show_in_menu": obj.category.show_in_menu,
        }

    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=ItemCategory.objects.all(),
        write_only=True,
    )

    class Meta:
        model  = ItemMaster
        fields = [
            'id', 'name', 'code', 'price_regular',
            'duration_min', 'apply_service',
            'exclude_from_payout', 'track_stock',
            'category', 'category_id',
            'route',
        ]

class BillCastStayMini(serializers.ModelSerializer):
    class Meta:
        model  = BillCastStay
        fields = ('cast',)           # cast は {id, stage_name} で返る


class BillCastStayMiniSerializer(serializers.ModelSerializer):
    cast_id = serializers.PrimaryKeyRelatedField(
        source='cast', queryset=Cast.objects.all(), write_only=True
    )
    # UIトグル（WRITE用）
    is_honshimei = serializers.BooleanField(required=False)
    is_dohan     = serializers.BooleanField(required=False)

    class Meta:
        model  = BillCastStay
        fields = ('id', 'cast_id', 'stay_type', 'is_honshimei', 'is_dohan', 'entered_at', 'left_at')
        read_only_fields = ('entered_at', 'left_at')

    # ---- 正規化（stay_type とトグルの整合）----
    def _normalize(self, attrs):
        st  = attrs.get('stay_type')
        hon = attrs.pop('is_honshimei', None)
        doh = attrs.pop('is_dohan', None)

        # 併用不可
        if hon is True and doh is True:
            raise serializers.ValidationError({'non_field_errors': ['本指名と同伴は同時指定できません。']})

        # トグル優先で stay_type 決定
        if doh is True:
            st = 'dohan'
        elif hon is True:
            st = 'nom'
        elif doh is False and st == 'dohan':
            st = 'free'
        elif hon is False and st == 'nom':
            st = 'free'

        if st:
            attrs['stay_type'] = st
        return attrs

    def validate(self, attrs):
        return self._normalize(dict(attrs))

    def create(self, vd):
        return super().create(self._normalize(vd))

    def update(self, inst, vd):
        return super().update(inst, self._normalize(vd))



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
                secure=True     # https:// 付与
            )[0]
        return None


class CastPayoutDetailSerializer(serializers.ModelSerializer):
    cast = CastMiniSerializer(read_only=True)
    bill      = BillMiniSerializer(read_only=True)
    bill_item = BillItemMiniSerializer(read_only=True)
    stay_type = serializers.SerializerMethodField()

    class Meta:
        model  = CastPayout
        fields = ('id', 'amount', 'bill', 'bill_item', 'cast', 'stay_type')

    def get_stay_type(self, obj):
        # 該当伝票でのそのキャストの最新 stay を見る（entered_at の新しいもの）
        try:
            s = obj.bill.stays.filter(cast_id=obj.cast_id).order_by('-entered_at').first()
            return getattr(s, 'stay_type', None) if s else None   # 'nom' | 'in' | 'free' | 'dohan' | None
        except Exception:
            return None
  


class BillItemSerializer(serializers.ModelSerializer):
    # --------------------<<  WRITE 用  >>--------------------
    # 送信時は ID だけ受け取るフィールド
    served_by_cast_id = serializers.PrimaryKeyRelatedField(
        source='served_by_cast',             # ← Model フィールド名
        queryset=Cast.objects.all(),
        write_only=True,                     # ← 書き込み専用
        required=False,
        allow_null=True,    # ← null を許容
    )
    code = serializers.CharField(
        source='item_master.code',            # ← ★追加
        read_only=True)
    duration_min  = serializers.IntegerField(
        source='item_master.duration_min',    # ← ★追加（あれば便利）
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
    
    # ───────── バリデーション（締め済みでも修正OK前提で極端値を防ぐ） ─────────
    def validate_qty(self, value):
        """数量: 1〜99の範囲"""
        if value is None:
            raise serializers.ValidationError(ERROR_MESSAGES['qty_zero'])
        if value < BILLITEM_QTY_MIN:
            raise serializers.ValidationError(ERROR_MESSAGES['qty_zero'])
        if value > BILLITEM_QTY_MAX:
            raise serializers.ValidationError(ERROR_MESSAGES['qty_range'])
        return value
    
    def validate_price(self, value):
        """単価: 0〜2,000,000の範囲"""
        if value is None:
            return value  # null許容の場合
        if value < BILLITEM_PRICE_MIN:
            raise serializers.ValidationError(ERROR_MESSAGES['price_negative'])
        if value > BILLITEM_PRICE_MAX:
            raise serializers.ValidationError(ERROR_MESSAGES['price_range'])
        return value
    
    def validate(self, attrs):
        """全体整合性チェック + Store-Locked確認"""
        # item_master の Store-Locked チェック
        item_master = attrs.get('item_master')
        if item_master:
            request = self.context.get('request')
            if request:
                # X-Store-Id ヘッダーから店舗IDを取得
                store_id = request.META.get('HTTP_X_STORE_ID') or request.META.get('HTTP_X_STORE_Id')
                if store_id and hasattr(item_master, 'store_id'):
                    if str(item_master.store_id) != str(store_id):
                        raise serializers.ValidationError({
                            'item_master': ERROR_MESSAGES['item_master_wrong_store']
                        })
        
        return attrs


class CastCategoryRateSerializer(serializers.ModelSerializer):

    category = serializers.SlugRelatedField(slug_field='code', queryset=ItemCategory.objects.all())
    class Meta:
        model  = CastCategoryRate
        fields = ('id','category','rate_free','rate_nomination','rate_inhouse')


User = get_user_model()

class CastSerializer(serializers.ModelSerializer):
    # ---------- 店が入力する write-only ----------
    username_in   = serializers.CharField(write_only=True, required=False, allow_blank=True)
    first_name_in = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name_in  = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # ---------- 取得時に返す read-only ----------
    username_read   = serializers.CharField(source='user.username',   read_only=True)
    first_name_read = serializers.CharField(source='user.first_name', read_only=True)
    last_name_read  = serializers.CharField(source='user.last_name',  read_only=True)

    avatar_url     = serializers.SerializerMethodField()
    category_rates = CastCategoryRateSerializer(many=True, required=False)

    # store は View 側で require_store 済み。来ていれば尊重、無ければ補完する。
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), required=False, write_only=True)
    hourly_wage = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model  = Cast
        fields = (
            "id", "stage_name", "store",
            # User 表示
            "username_read","first_name_read","last_name_read",
            # User 入力（新規/任意更新）
            "username_in","first_name_in","last_name_in",
            # 給与・画像
            "hourly_wage","avatar","avatar_url",
            # 個別バック率
            "back_rate_free_override","back_rate_nomination_override","back_rate_inhouse_override",
            # カテゴリ別バック率
            "category_rates",
        )

    # ---------- helpers ----------
    def get_avatar_url(self, obj):
        av = getattr(obj, 'avatar', None)
        try:
            return av.url if av else None
        except Exception:
            return None

    # ---------- create ----------
    def create(self, validated_data):
        rates = validated_data.pop('category_rates', [])
        username = (validated_data.pop('username_in', '') or '').strip()
        fn = (validated_data.pop('first_name_in', '') or '').strip()
        ln = (validated_data.pop('last_name_in', '') or '').strip()

        if not username:
            raise serializers.ValidationError({'username_in': 'ユーザー名は必須です。'})
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError({'username_in': 'このユーザー名は既に使用されています。'})

        # store 補完（View で request.store セット済み想定）
        req = self.context.get('request')
        if not validated_data.get('store') and req is not None:
            st = getattr(req, 'store', None)
            if st:
                validated_data['store'] = st

        user = User.objects.create_user(
            username=username,
            password=get_random_string(12),
            first_name=fn, last_name=ln,
        )
        cast = Cast.objects.create(user=user, **validated_data)

        # 初期サマリ（必要なら）
        try:
            CastDailySummary.objects.get_or_create(
                cast=cast, store=cast.store, work_date=CastDailySummary._meta.get_field('work_date').default() if hasattr(CastDailySummary._meta.get_field('work_date'), 'default') else None,
                defaults=dict(worked_min=0, payroll=0, sales_free=0, sales_in=0, sales_nom=0, sales_champ=0)
            )
        except Exception:
            pass

        # カテゴリ別バック率
        self._sync_rates(cast, rates)
        return cast

    # ---------- update ----------
    def update(self, instance, validated_data):
        # username_in を送ってきた時だけ “変更を許可（重複チェック付き）”
        uname = validated_data.pop('username_in', None)
        fn    = validated_data.pop('first_name_in', None)
        ln    = validated_data.pop('last_name_in', None)

        user = instance.user
        if uname is not None:
            u = uname.strip()
            if not u:
                raise serializers.ValidationError({'username_in': '空にはできません。'})
            if u != user.username and User.objects.filter(username=u).exists():
                raise serializers.ValidationError({'username_in': 'このユーザー名は既に使用されています。'})
            user.username = u
        if fn is not None:
            user.first_name = fn
        if ln is not None:
            user.last_name = ln
        if uname is not None or fn is not None or ln is not None:
            user.save(update_fields=['username','first_name','last_name'])

        rates = validated_data.pop('category_rates', None)

        # store が未指定なら据え置き（View 側で require_store）
        cast = super().update(instance, validated_data)
        if rates is not None:
            self._sync_rates(cast, rates)
        return cast

    def _sync_rates(self, cast, rates):
        CastCategoryRate.objects.filter(cast=cast).delete()
        for r in (rates or []):
            CastCategoryRate.objects.create(cast=cast, **r)

class BillCastStaySerializer(serializers.ModelSerializer):
    cast = CastMiniSerializer()

    is_honshimei = serializers.BooleanField(read_only=True)
    is_dohan     = serializers.BooleanField(read_only=True)
    is_help      = serializers.BooleanField(read_only=True)

    class Meta:
        model  = BillCastStay
        fields = ("cast", "stay_type", "is_honshimei", "is_dohan", "entered_at", "left_at", "is_help")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        st = instance.stay_type
        data["is_honshimei"] = (st == "nom")
        data["is_dohan"]     = (st == "dohan")
        data["is_help"]      = bool(getattr(instance, "is_help", False))
        return data


class CustomerTagSerializer(serializers.ModelSerializer):
    """顧客タグ"""
    class Meta:
        model = CustomerTag
        fields = ('id', 'code', 'name', 'color', 'is_active')


class CustomerSerializer(serializers.ModelSerializer):
    # タグを読み取り・書き込み両対応
    tags = CustomerTagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        source='tags',
        many=True,
        queryset=CustomerTag.objects.all(),
        required=False,
        write_only=True
    )
    
    # 派生：タグ名を comma-separated で返す（リスト表示で便利）
    tag_names = serializers.SerializerMethodField()
    
    # ★ 最終来店日時（直近伝票から算出）
    last_visit_at = serializers.SerializerMethodField()
    
    # ★ 最終担当キャスト（ミニ形式）
    last_cast_obj = CastMiniSerializer(source='last_cast', read_only=True)
    
    class Meta:
        model  = Customer
        fields = (
            'id', 'full_name', 'alias', 'phone', 'birthday', 'photo', 'memo',
            'tags', 'tag_ids', 'tag_names',
            'has_bottle', 'bottle_shelf', 'bottle_memo',
            'last_drink', 'last_cast', 'last_visit_at', 'last_cast_obj',
            'created_at', 'updated_at'
        )
        read_only_fields = ('last_drink', 'last_cast', 'last_visit_at', 'last_cast_obj', 'created_at', 'updated_at')
    
    def get_tag_names(self, obj):
        """タグ名をカンマ区切りで返す（検索・フィルタ用）"""
        return ', '.join(obj.tags.values_list('name', flat=True))
    
    def get_last_visit_at(self, obj):
        """直近伝票から最終来店日時を算出（closed_at優先、無ければopened_at）"""
        latest = obj.bills.order_by('-closed_at', '-opened_at').values('closed_at', 'opened_at').first()
        if latest:
            return latest.get('closed_at') or latest.get('opened_at')
        return None


class CustomerLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model  = CustomerLog
        fields = ('id', 'action', 'user_name', 'payload', 'at')

class BillDiscountLineSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = BillDiscountLine
        fields = ('id', 'label', 'amount', 'sort_order')



class BillSerializer(serializers.ModelSerializer):
    table        = TableMiniSerializer(read_only=True)
    items        = BillItemSerializer(read_only=True, many=True)
    stays        = BillCastStaySerializer(read_only=True, many=True)

    # 金額は締め済みなら保存値、未締めなら Calculator で算出（下の get_* 参照）
    subtotal        = serializers.SerializerMethodField()
    service_charge  = serializers.SerializerMethodField()
    tax             = serializers.SerializerMethodField()
    grand_total     = serializers.SerializerMethodField()

    inhouse_casts = CastSerializer(many=True, read_only=True)
    opened_at     = serializers.DateTimeField(required=False, allow_null=True)
    expected_out  = serializers.DateTimeField(required=False, allow_null=True)
    set_rounds    = serializers.IntegerField(read_only=True)
    ext_minutes   = serializers.IntegerField(read_only=True)
    pax           = serializers.IntegerField(required=False, default=0)

    main_cast      = serializers.PrimaryKeyRelatedField(
        queryset=Cast.objects.all(), allow_null=True, required=False
    )
    main_cast_obj  = CastMiniSerializer(source='main_cast', read_only=True)

    # WRITE: 本指名（既存の read 用 nominated_casts を維持しつつ書き込み用フィールドを追加）
    nominated_casts_w = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Cast.objects.all(), required=False, write_only=True
    )

    customer_ids = serializers.PrimaryKeyRelatedField(
        source='customers', many=True,
        queryset=Customer.objects.all(),
        required=False, write_only=True
    )
    customers = CustomerSerializer(many=True, read_only=True)
    customer_display_name = serializers.SerializerMethodField()

    # WRITE: 卓
    table_id = serializers.PrimaryKeyRelatedField(
        source='table',
        queryset=Table.objects.all(),
        allow_null=True, required=False, write_only=True,
    )

    # WRITE: 場内/フリー 他
    free_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Cast.objects.all(),
        required=False, write_only=True,
    )
    inhouse_casts_w = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Cast.objects.all(),
        required=False, write_only=True
    )

    change_due  = serializers.SerializerMethodField()
    paid_total  = serializers.IntegerField(read_only=True)

    discount_rule = serializers.PrimaryKeyRelatedField(
        queryset=DiscountRule.objects.all(),   # __init__ で store による絞り込み
        required=False, allow_null=True
    )

    # ★ 手入力割引：入出力
    manual_discounts = BillDiscountLineSerializer(many=True, required=False)
    manual_discount_total = serializers.SerializerMethodField(read_only=True)
    
    # ★ 給与スナップショット・dirty 判定
    payroll_snapshot = serializers.JSONField(read_only=True)
    payroll_dirty = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bill
        fields = (
            # ---- 基本 ----
            "id", "table", "table_id", "opened_at", "closed_at","memo", "pax",
            # ---- 金額 ----
            "subtotal", "service_charge", "tax", "grand_total", "total",
            "paid_cash","paid_card","paid_total","change_due",
            # ---- 関連 ----
            "items", "stays","expected_out",
            "nominated_casts",            # READ (depth=2)
            "nominated_casts_w",          # WRITE
            "settled_total",
            "inhouse_casts",        # READ
            "inhouse_casts_w",      # WRITE
            "free_ids","set_rounds","ext_minutes",
            "main_cast", "main_cast_obj",
            "customers", "customer_ids", "customer_display_name",
            # ---- 割引 ----
            "discount_rule",
            "manual_discounts", "manual_discount_total",
            # ---- 給与スナップショット ----
            "payroll_snapshot", "payroll_dirty",
        )
        read_only_fields = (
            "subtotal", "service_charge", "tax", "grand_total", "total",
            "closed_at", "set_rounds","ext_minutes",
            "paid_total","change_due",
            "manual_discount_total",
            "payroll_snapshot", "payroll_dirty",
        )
        depth = 2

    # ---- init：discount_rule を店舗で絞る ----
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        req = self.context.get('request')
        qs = DiscountRule.objects.filter(is_active=True)
        if req and getattr(req, 'store', None):
            qs = qs.filter(store=req.store)
        self.fields['discount_rule'].queryset = qs

    # ---- バリデーション ----
    def validate_paid_cash(self, value):
        """
        支払額（現金）のバリデーション：0円以上、上限以下をチェック。
        """
        if value is None:
            return value
        if value < BILL_PAYMENT_MIN:
            raise serializers.ValidationError(ERROR_MESSAGES['bill_payment_negative'])
        if value > BILL_PAYMENT_MAX:
            raise serializers.ValidationError(ERROR_MESSAGES['bill_payment_too_large'])
        return value

    def validate_paid_card(self, value):
        """
        支払額（カード）のバリデーション：0円以上、上限以下をチェック。
        """
        if value is None:
            return value
        if value < BILL_PAYMENT_MIN:
            raise serializers.ValidationError(ERROR_MESSAGES['bill_payment_negative'])
        if value > BILL_PAYMENT_MAX:
            raise serializers.ValidationError(ERROR_MESSAGES['bill_payment_too_large'])
        return value

    def validate(self, data):
        """
        伝票全体のバリデーション：支払額合計が grand_total を過剰に超えないかチェック。
        締め済み伝票でも修正可能だが、極端な値や不整合を防ぐ。
        """
        # paid_cash/paid_card が両方 None の場合はスキップ（未設定 or 更新なし）
        paid_cash = data.get('paid_cash')
        paid_card = data.get('paid_card')
        if paid_cash is None and paid_card is None:
            return data

        # 既存インスタンス（更新時）または新規作成時の値を取得
        if self.instance:
            paid_cash = paid_cash if paid_cash is not None else (self.instance.paid_cash or 0)
            paid_card = paid_card if paid_card is not None else (self.instance.paid_card or 0)
        else:
            paid_cash = paid_cash or 0
            paid_card = paid_card or 0

        paid_total = paid_cash + paid_card

        # grand_total を計算（更新時は既存値を使用、新規作成時は 0）
        if self.instance:
            grand_total = self.get_grand_total(self.instance)
        else:
            grand_total = 0  # 新規作成時は BillItem がないため 0

        # 支払額が grand_total を BILL_OVERPAY_TOLERANCE 以上超えないかチェック
        if paid_total > grand_total + BILL_OVERPAY_TOLERANCE:
            raise serializers.ValidationError(ERROR_MESSAGES['bill_overpaid'])

        return data

    # ---- READ helper ----
    def _is_closed(self, obj): return bool(getattr(obj, "closed_at", None))
    def _calc(self, obj):
        res = getattr(obj, "_calc_cache", None)
        if res is None:
            from .calculator import BillCalculator
            obj._calc_cache = res = BillCalculator(obj).execute()
        return res

    def get_subtotal(self, obj):       return int(obj.subtotal)       if self._is_closed(obj) else int(self._calc(obj).subtotal)
    def get_service_charge(self, obj): return int(obj.service_charge) if self._is_closed(obj) else int(self._calc(obj).service_fee)
    def get_tax(self, obj):            return int(obj.tax)            if self._is_closed(obj) else int(self._calc(obj).tax)
    def get_grand_total(self, obj):    return int(obj.total or obj.grand_total or 0) if self._is_closed(obj) else int(self._calc(obj).total)

    def get_change_due(self, obj):
        st = obj.settled_total if obj.settled_total is not None else self.get_grand_total(obj)
        st = st or 0
        return max(0, obj.paid_total - st)

    def get_customer_display_name(self, obj):
        first = obj.customers.first()
        return first.display_name if first else ''

    def get_payroll_dirty(self, obj):
        """
        payroll_dirty 判定：snapshot が存在し、
        現在の計算ハッシュが snapshot ハッシュと異なる場合 True。
        """
        from billing.services import is_payroll_dirty
        return is_payroll_dirty(obj)

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        first = obj.customers.first()
        rep['customer_display_name'] = first.display_name if first else ''
        return rep

    def get_manual_discount_total(self, obj):
        return obj.manual_discounts.aggregate(s=Sum('amount'))['s'] or 0

    # ---- 手入力割引：全入れ替え ----
    def _replace_manual_discounts(self, bill: Bill, rows):
        bill.manual_discounts.all().delete()
        to_create = []
        for idx, r in enumerate(rows or []):
            label = (r.get('label') or '').strip()
            amount = int(r.get('amount') or 0)
            if amount <= 0:
                continue
            sort_order = r.get('sort_order', idx)
            to_create.append(BillDiscountLine(
                bill=bill, label=label, amount=amount, sort_order=sort_order
            ))
        if to_create:
            BillDiscountLine.objects.bulk_create(to_create)

    # ---- CREATE：opened_at 補完＋手入力割引＋指名/場内同期 ----
    @transaction.atomic
    def create(self, validated_data):
        if validated_data.get('opened_at') is None:
            validated_data['opened_at'] = timezone.now()

        # まず配列系を抜く
        nominated = validated_data.pop("nominated_casts_w", [])
        inhouse   = validated_data.pop("inhouse_casts_w", [])
        cust_ids  = validated_data.pop('customer_ids', None)
        rows      = validated_data.pop('manual_discounts', None)

        bill = Bill.objects.create(**validated_data)

        if nominated:
            bill.nominated_casts.set(nominated)
        if cust_ids is not None:
            bill.customers.set(cust_ids)
        if rows is not None:
            self._replace_manual_discounts(bill, rows)

        # 指名/場内差分 → 料金行同期（既存の関数）
        sync_nomination_fees(
            bill,
            prev_main=set(),
            new_main=set(nominated),
            prev_in=set(),
            new_in=set(inhouse),
        )
        return bill

    # ---- UPDATE：手入力割引＋本体更新を統合 ----
    @transaction.atomic
    def update(self, instance, validated_data):
        # opened_at の更新許可＋ロールに応じた最小ガード
        req = self.context.get('request')
        new_opened_at = validated_data.get('opened_at', None)

        if new_opened_at is not None and req is not None:
            try:
                is_staff_user = Staff.objects.filter(user=req.user).exists()
            except Exception:
                is_staff_user = False

            if is_staff_user:
                try:
                    # 当日判定（タイムゾーン考慮）: 伝票が本日分である場合のみ staff は更新可
                    bill_date = None
                    if instance.opened_at:
                        bill_date = timezone.localtime(instance.opened_at).date()
                    today_local = timezone.localdate()
                    if bill_date != today_local:
                        from rest_framework import serializers as drf_serializers
                        raise drf_serializers.ValidationError({
                            'opened_at': 'スタッフは当日伝票のみ変更できます。'
                        })
                except Exception:
                    # 何らかの理由で安全に判定できない場合は弾く（保守的）
                    from rest_framework import serializers as drf_serializers
                    raise drf_serializers.ValidationError({
                        'opened_at': 'opened_at の更新が許可されていません。'
                    })

        # 更新前スナップ
        prev_main = set(instance.nominated_casts.values_list("id", flat=True))
        prev_in   = set(instance.stays.filter(stay_type="in", left_at__isnull=True).values_list("cast_id", flat=True))
        prev_dohan = set(instance.stays.filter(stay_type='dohan', left_at__isnull=True).values_list('cast_id', flat=True))

        # 配列を先に抜き出す
        cust_ids      = validated_data.pop('customer_ids', None)
        nominated_raw = validated_data.pop("nominated_casts_w", None)
        inhouse_raw   = validated_data.pop("inhouse_casts_w", None)
        free_raw      = validated_data.pop("free_ids", None)
        rows          = validated_data.pop('manual_discounts', None)

        help_raw = self.context['request'].data.get('help_ids', None)
        to_ids = lambda raw: [c.id if hasattr(c, 'id') else c for c in (raw or [])]
        help_ids = set(to_ids(help_raw)) if help_raw is not None else set()

        # discount_rule が来なければ現状維持
        if 'discount_rule' not in validated_data:
            validated_data['discount_rule'] = instance.discount_rule

        # 通常フィールドをまとめて更新
        opened_at_was_changed = ('opened_at' in validated_data)
        instance = super().update(instance, validated_data)

        # opened_at を変更した場合は expected_out を再計算
        # さらに closed_at が既にある（締め済み）かつ closed_at を明示更新していないときは
        # 新しい opened_at に基づく expected_out へ closed_at を合わせる（自動整合）
        if opened_at_was_changed:
            try:
                instance.update_expected_out(save=True)
                if instance.closed_at and ('closed_at' not in validated_data):
                    instance.closed_at = instance.expected_out
                    instance.save(update_fields=['closed_at'])
            except Exception:
                pass

        # 顧客M2M
        if cust_ids is not None:
            instance.customers.set(cust_ids)

        # 手入力割引の入れ替え
        if rows is not None:
            self._replace_manual_discounts(instance, rows)

        # --- 以下、指名/場内/フリー/同伴の同期（元コードを維持） ---
        to_ids = lambda raw: [c.id if hasattr(c, 'id') else c for c in (raw or [])]
        nominated_ids = set(to_ids(nominated_raw)) if nominated_raw is not None else prev_main
        inhouse_ids   = set(to_ids(inhouse_raw)) if inhouse_raw is not None else prev_in
        free_ids_orig = set(to_ids(free_raw)) if free_raw is not None else set()

        stay_map = {s.cast_id: s for s in instance.stays.all()}

        # 本指名
        if nominated_raw is not None:
            instance.nominated_casts.set(list(nominated_ids))
            for cid in nominated_ids:
                st = stay_map.get(cid)
                if not st:
                    BillCastStay.objects.create(
                        bill=instance, cast_id=cid,
                        entered_at=timezone.now(), stay_type="nom",
                        is_honshimei=True, is_help=False         # ← 追加（明示）
                    )
                else:
                    if st.stay_type != "nom" or st.left_at:
                        st.stay_type = "nom"; st.left_at = None
                    if not getattr(st, 'is_honshimei', False):
                        st.is_honshimei = True
                    st.is_help = False                           # ← 追加（明示）
                    st.save(update_fields=["stay_type","left_at","is_honshimei","is_help"])  # ← 追加

            for cid, st in stay_map.items():
                if cid not in nominated_ids and st.stay_type == "nom":
                    st.stay_type = "in" if cid in inhouse_ids else "free"
                    if getattr(st, 'is_honshimei', False):
                        st.is_honshimei = False
                        st.save(update_fields=["stay_type","is_honshimei"])
                    else:
                        st.save(update_fields=["stay_type"])

        # 場内
        if inhouse_raw is not None:
            for cid in inhouse_ids:
                st = stay_map.get(cid)
                if not st:
                    BillCastStay.objects.create(
                        bill=instance, cast_id=cid,
                        entered_at=timezone.now(), stay_type="in",
                        is_help=False                            # ← 追加
                    )
                else:
                    if st.stay_type != "in" or st.left_at:
                        st.stay_type = "in"; st.left_at = None
                    st.is_help = False                          # ← 追加
                    st.save(update_fields=["stay_type","left_at","is_help"])  # ← 追加
            for cid, st in stay_map.items():
                if cid not in inhouse_ids and st.stay_type == "in":
                    st.stay_type = "free"; st.save(update_fields=["stay_type"])

        # フリー
        if free_raw is not None:
            free_ids = [cid for cid in free_ids_orig if cid not in inhouse_ids and cid not in nominated_ids]
            for cid in free_ids:
                st = stay_map.get(cid)
                if not st or st.left_at:
                    BillCastStay.objects.create(
                        bill=instance, cast_id=cid,
                        entered_at=timezone.now(), stay_type="free"
                    )
                elif st.stay_type != "free":
                    st.stay_type = "free"; st.save(update_fields=["stay_type"])
            active_free = instance.stays.filter(stay_type="free", left_at__isnull=True)
            for st in active_free:
                if st.cast_id not in free_ids:
                    st.left_at = timezone.now()
                    st.save(update_fields=["left_at"])

        # --- free (free_raw) の処理が終わった直後に「is_help 付与/解除」を反映 ---
        if free_raw is not None or help_raw is not None:
            stay_map = {s.cast_id: s for s in instance.stays.all()}
            # いまアクティブな free を抽出
            active_free = instance.stays.filter(stay_type="free", left_at__isnull=True)
            for s in active_free:
                if help_raw is None:
                    # help_ids が送られていないときは既存値を維持
                    continue
                # help_ids に含まれていれば is_help=True、なければ False
                s.is_help = s.cast_id in help_ids
                s.save(update_fields=["is_help"])

        # 同伴（dohan）
        dohan_raw = self.context['request'].data.get('dohan_ids', None)
        if dohan_raw is not None:
            dohan_ids = set(to_ids(dohan_raw))
            # 変更前の同伴キャスト集合（差分用に保持）
            prev_dohan_before = set(instance.stays.filter(stay_type='dohan', left_at__isnull=True)
                                            .values_list('cast_id', flat=True))

            # 追加 / 更新
            for cid in dohan_ids:
                st = stay_map.get(cid)
                if not st:
                    BillCastStay.objects.create(
                        bill=instance, cast_id=cid,
                        entered_at=timezone.now(), stay_type='dohan',
                        is_help=False
                    )
                else:
                    if st.stay_type != 'dohan' or st.left_at:
                        st.stay_type = 'dohan'; st.left_at = None
                    st.is_help = False
                    st.save(update_fields=['stay_type','left_at','is_help'])
                # 同伴指定時は本指名から外す（排他）
                instance.nominated_casts.remove(cid)

            # 削除（今回送ってこなかった同伴 → free 化）
            for cid in (prev_dohan_before - dohan_ids):
                st = stay_map.get(cid)
                if st:
                    st.stay_type = 'free'
                    st.save(update_fields=['stay_type'])

            # --- 同伴料行の差分同期（前集合 vs 今回指定集合） ---
            from .services import sync_dohan_fees
            sync_dohan_fees(instance, prev_dohan=prev_dohan_before, new_dohan=dohan_ids)



        # 料金行を差分同期
        sync_nomination_fees(
            instance,
            prev_main, set(instance.nominated_casts.values_list('id', flat=True)),
            prev_in,   set(instance.stays.filter(stay_type='in', left_at__isnull=True)
                                .values_list('cast_id', flat=True)),
        )
        return instance


class CastShiftSerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(
        source='store', queryset=Store.objects.all(),
        write_only=True, required=False
    )
    plan_start    = serializers.DateTimeField(required=False, allow_null=True)
    plan_end    = serializers.DateTimeField(required=False, allow_null=True)
    store     = serializers.CharField(source='store.name', read_only=True)
    cast     = CastMiniSerializer(read_only=True)
    cast_id  = serializers.PrimaryKeyRelatedField(
        source='cast', queryset=Cast.objects.all(), write_only=True
    )

    minutes_worked = serializers.IntegerField(read_only=True)
    payroll_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model  = CastShift
        fields = (
            'id', 'store', 'store_id',
            'cast', 'cast_id',
            'plan_start', 'plan_end',
            'clock_in', 'clock_out',
            'hourly_wage_snap',
            'minutes_worked', 'payroll_amount','worked_min',
        )
        read_only_fields = ('hourly_wage_snap',)

    def validate(self, attrs):
        ci, co = attrs.get('clock_in'), attrs.get('clock_out')
        if ci and co and ci > co:
            raise serializers.ValidationError(
                {'clock_out': 'clock_out は clock_in より後にしてください'}
            )
        return attrs
    
    def create(self, validated):
        # store が無ければ (1) request.store → (2) cast.store の順で補完
        if not validated.get('store'):
            req_store = self.context['request'].store
            validated['store'] = req_store or validated['cast'].store
        return super().create(validated)



class CastDailySummarySerializer(serializers.ModelSerializer):
    cast   = CastMiniSerializer(read_only=True)
    store  = serializers.StringRelatedField(read_only=True)   # “ジャングル東京” など
    # 派生フィールド
    worked_h = serializers.SerializerMethodField()
    total    = serializers.SerializerMethodField()            # 歩合＋時給

    class Meta:
        model  = CastDailySummary
        fields = (
            'id', 'store', 'cast', 'work_date',
            'worked_min', 'worked_h',
            'payroll',
            'sales_free', 'sales_in', 'sales_nom', 'sales_champ',
            'total',
        )
        read_only_fields = fields

    # ───── 派生値 ────────────────────────────
    def get_worked_h(self, obj):
        return round(obj.worked_min / 60, 2) if obj.worked_min else 0

    def get_total(self, obj):
        return (
            obj.payroll + obj.sales_free + obj.sales_in + obj.sales_nom + obj.sales_champ
        )


class CastRankingSerializer(serializers.ModelSerializer):
    cast_id    = serializers.IntegerField(source='id', read_only=True)  # ← ★追加
    revenue    = serializers.IntegerField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model  = Cast
        fields = ('cast_id',      # ← こちらを公開
                  'stage_name',
                  'revenue',
                  'avatar_url')   # id は除外したので OK

    def get_avatar_url(self, obj):
        if obj.avatar:
            url, _ = cloudinary_url(
                obj.avatar.public_id,
                format=obj.avatar.format,
                width=240, height=240, crop='thumb',
                secure=True,
            )
            return url
        return static('img/user-default.png')



class StaffSerializer(serializers.ModelSerializer):
    # ---- 読み取り用（編集画面に出す） ----
    username    = serializers.CharField(source='user.username', read_only=True)
    first_name  = serializers.CharField(source='user.first_name', read_only=True)
    last_name   = serializers.CharField(source='user.last_name', read_only=True)
    role_code   = serializers.CharField(source='role', read_only=True)
    # stores は ID 配列で入出力（ID/PKで OK）
    stores      = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), many=True, required=False
    )

    # ---- 書き込み用（新規作成/更新）※write_only ----
    username_in   = serializers.CharField(write_only=True, required=False, allow_blank=True)
    first_name_in = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name_in  = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model  = Staff
        fields = [
            'id',
            'username', 'first_name', 'last_name',   # 読み取り
            'username_in', 'first_name_in', 'last_name_in',  # 書き込み
            'role_code', 'role', 'hourly_wage', 'stores',
        ]
        extra_kwargs = {
            'role': {'required': False},
            'hourly_wage': {'required': False},
        }

    def create(self, validated_data):
        # write_only を取り出し
        uname = validated_data.pop('username_in', '').strip()
        fn    = validated_data.pop('first_name_in', '').strip()
        ln    = validated_data.pop('last_name_in', '').strip()

        if not uname:
            raise serializers.ValidationError({'username_in': 'ユーザー名は必須です。'})
        if User.objects.filter(username=uname).exists():
            raise serializers.ValidationError({'username_in': 'このユーザー名は既に使用されています。'})

        user = User.objects.create(username=uname, first_name=fn, last_name=ln, is_active=True)
        stores = validated_data.pop('stores', [])
        staff = Staff.objects.create(user=user, **validated_data)

        # stores 明示がなければ “現在店舗” を自動付与
        req = self.context.get('request')
        if stores:
            staff.stores.set(stores)
        elif req and getattr(req, 'store', None):
            staff.stores.add(req.store.id)

        return staff

    def update(self, instance, validated_data):
        # user 氏名の更新（任意）
        fn = validated_data.pop('first_name_in', None)
        ln = validated_data.pop('last_name_in', None)
        if fn is not None:
            instance.user.first_name = fn
        if ln is not None:
            instance.user.last_name = ln
        if fn is not None or ln is not None:
            instance.user.save(update_fields=['first_name','last_name'])

        # stores / role / hourly_wage の更新
        stores = validated_data.pop('stores', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if stores is not None:
            instance.stores.set(stores)

        return instance

class StaffShiftSerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(
        source='store', queryset=Store.objects.all(),
        write_only=True, required=False
    )
    staff_id = serializers.PrimaryKeyRelatedField(
        source='staff',
        queryset=Staff.objects.all(),
        # これで「読み書き OK」→ レスポンスにも id が載る
    )
    staff = serializers.StringRelatedField(read_only=True)
    store = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model  = StaffShift
        fields = (
            'id', 'store', 'store_id',
            'staff', 'staff_id',
            'plan_start', 'plan_end',
            'clock_in', 'clock_out',
            'hourly_wage_snap', 'worked_min', 'payroll_amount',
        )
        read_only_fields = ('hourly_wage_snap', 'worked_min', 'payroll_amount')

    def create(self, validated):
        # ① store が無ければ request.store
        if not validated.get('store'):
            validated['store'] = self.context['request'].store

        # ② まだ無ければ staff.stores.first() を補完
        if not validated.get('store'):
            st = validated['staff'].stores.first()
            if st:
                validated['store'] = st

        return super().create(validated)




from rest_framework import serializers
from django.utils import timezone
from .models import StoreNotice

class StoreNoticeSerializer(serializers.ModelSerializer):
    store = serializers.PrimaryKeyRelatedField(read_only=True)
    cover_url = serializers.SerializerMethodField()
    cover_clear = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = StoreNotice
        fields = (
            'id', 'store', 'title', 'body',
            'cover', 'cover_url', 'cover_clear',
            'is_published', 'publish_at', 'pinned',
            'created_at', 'updated_at',
        )
        read_only_fields = ('store','created_at', 'updated_at')

    def get_cover_url(self, obj):
        try:
            url = obj.cover.url
        except Exception:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def validate(self, attrs):
        # is_published が True で publish_at 未指定なら “今” を自動設定（管理画面の使い勝手向上）
        if attrs.get('is_published') and not attrs.get('publish_at'):
            attrs['publish_at'] = timezone.now()
        return attrs
    
    def create(self, validated_data):
        # ★ ここが肝：モデルに無いフィールドを取り除く
        validated_data.pop('cover_clear', None)
        return super().create(validated_data)


    def update(self, instance, validated_data):
        clear = validated_data.pop('cover_clear', False)
        # cover を新規アップロードしつつ clear 指定は無視する
        inst = super().update(instance, validated_data)
        if clear and 'cover' not in validated_data:
            # 既存ファイルを削除してフィールドを空に
            if inst.cover:
                inst.cover.delete(save=False)
            inst.cover = None
            inst.save(update_fields=['cover'])
        return inst
    
    
    
    
# billing/serializers.py
from rest_framework import serializers
from .models import OrderTicket

class OrderTicketSerializer(serializers.ModelSerializer):
    table_no     = serializers.SerializerMethodField()
    item_name    = serializers.SerializerMethodField()
    ordered_by   = serializers.SerializerMethodField()
    elapsed_sec  = serializers.SerializerMethodField()

    class Meta:
        model  = OrderTicket
        fields = ('id', 'route', 'state', 'created_at',
                  'table_no', 'item_name', 'ordered_by', 'elapsed_sec')

    def get_table_no(self, obj):
        try:
            tbl = getattr(getattr(obj.bill_item, 'bill', None), 'table', None)
            return (getattr(tbl, 'code', '') or '') if tbl else ''
        except Exception:
            return None

    def get_item_name(self, obj):
        # BillItem.name を優先（価格確定後の名前）
        name = getattr(obj.bill_item, 'name', None)
        if name:
            return name
        im = getattr(obj.bill_item, 'item_master', None)
        return getattr(im, 'name', None)

    def get_ordered_by(self, obj):
        return 'cast' if obj.created_by_cast else 'staff'

    def get_elapsed_sec(self, obj):
        from django.utils import timezone
        return int((timezone.now() - obj.created_at).total_seconds())


from rest_framework import serializers
from .models import Staff

class StaffMiniSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model  = Staff
        fields = ('id', 'name', 'role')

    def get_name(self, obj):
        u = getattr(obj, 'user', None)
        return getattr(u, 'username', None) or f'ID:{obj.pk}'



# 末尾などに追記
from rest_framework import serializers
from .models import OrderTicket

class OrderTicketHistorySerializer(serializers.ModelSerializer):
    table_no   = serializers.SerializerMethodField()
    item_name  = serializers.SerializerMethodField()
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model  = OrderTicket
        fields = ('id', 'table_no', 'item_name', 'staff_name', 'taken_at')

    def get_table_no(self, obj):
        try:
            tbl = getattr(getattr(obj.bill_item, 'bill', None), 'table', None)
            return (getattr(tbl, 'code', '') or '') if tbl else ''
        except Exception:
            return None

    def get_item_name(self, obj):
        name = getattr(obj.bill_item, 'name', None)
        if name:
            return name
        im = getattr(obj.bill_item, 'item_master', None)
        return getattr(im, 'name', None)

    def get_staff_name(self, obj):
        st = getattr(obj, 'taken_by_staff', None)
        u  = getattr(st, 'user', None)
        return getattr(u, 'username', None) or (st and f'ID:{st.pk}') or '-'




class CastGoalSerializer(serializers.ModelSerializer):
    # READ 専用の進捗フィールド
    progress_value    = serializers.IntegerField(read_only=True)
    progress_ratio    = serializers.FloatField(read_only=True)
    progress_percent  = serializers.IntegerField(read_only=True)
    hits              = serializers.ListField(child=serializers.IntegerField(), read_only=True)

    # フロントの値 → モデルの choices へ
    METRIC_ALIASES = {
        'sales_amount'       : CastGoal.METRIC_REVENUE,
        'champagne_revenue'  : CastGoal.METRIC_CHAMP_REVENUE,
        'champagne_bottles'  : CastGoal.METRIC_CHAMP_COUNT,
        'nominations_count'  : CastGoal.METRIC_NOMINATIONS,
        'inhouse_count'      : CastGoal.METRIC_INHOUSE,
    }

    def validate_metric(self, value):
        return self.METRIC_ALIASES.get(value, value)

    class Meta:
        model  = CastGoal
        fields = (
            'id', 'cast', 'metric', 'target_value',
            'period_kind', 'start_date', 'end_date',
            'active', 'milestones_hit',
            'progress_value','progress_ratio','progress_percent','hits',
            'created_at','updated_at',
        )
        read_only_fields = (
            'cast','milestones_hit','created_at','updated_at',
            'progress_value','progress_ratio','progress_percent','hits',
        )

    def validate(self, attrs):
        cast = self.context.get('cast') or attrs.get('cast')
        if not cast:
            raise serializers.ValidationError('cast is required')
        if attrs.get('target_value') is None or attrs.get('target_value') <= 0:
            raise serializers.ValidationError({'target_value': 'must be positive'})

        # 上限 10 件（active のみカウント）
        if self.instance is None:
            if CastGoal.objects.filter(cast=cast, active=True).count() >= 10:
                raise serializers.ValidationError('active goals limit (10) exceeded')

        # custom のときは start/end 必須
        pk = attrs.get('period_kind') or getattr(self.instance, 'period_kind', CastGoal.PERIOD_DAILY)
        s  = attrs.get('start_date')  or getattr(self.instance, 'start_date', None)
        e  = attrs.get('end_date')    or getattr(self.instance, 'end_date', None)
        if pk == CastGoal.PERIOD_CUSTOM and (not s or not e):
            raise serializers.ValidationError({'start_date': 'required', 'end_date': 'required'})
        return attrs

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        pr  = instance.progress()
        rep['progress_value']   = pr['value']
        rep['progress_ratio']   = round(pr['ratio'], 4)
        rep['progress_percent'] = pr['percent']
        rep['hits']             = pr['hits']
        return rep



class DiscountRuleSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = DiscountRule
        fields = [
            'id', 'store', 'store_name', 'code', 'name',
            'amount_off', 'percent_off',
            'is_active', 'is_basic',
            'show_in_basics', 'show_in_pay',
            'sort_order', 'created_at',
        ]

    def validate(self, attrs):
        amt = attrs.get('amount_off', getattr(self.instance, 'amount_off', None))
        pct = attrs.get('percent_off', getattr(self.instance, 'percent_off', None))
        if not amt and not pct:
            raise serializers.ValidationError("amount_off か percent_off のどちらかを指定してください。")
        if amt and pct:
            raise serializers.ValidationError("amount_off と percent_off は同時に指定できません。")
        return attrs


# === 給与計算ページ ===


class CastPayoutBillMiniSerializer(serializers.ModelSerializer):
    table_no   = serializers.SerializerMethodField()
    opened_at  = serializers.DateTimeField(read_only=True)   # あると便利
    subtotal   = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Bill
        fields = ("id", "opened_at", "closed_at", "subtotal", "table_no")

    def get_table_no(self, obj):
        try:
            return getattr(obj.table, "code", None) or getattr(obj.table, "number", None)
        except Exception:
            return None

class CastPayoutBillItemMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BillItem
        fields = ("id", "name", "price", "qty", "is_inhouse")

class CastPayoutListSerializer(serializers.ModelSerializer):
    cast      = CastMiniSerializer(read_only=True)                 # ★ 一覧にも cast を
    bill      = CastPayoutBillMiniSerializer(read_only=True)
    bill_item = CastPayoutBillItemMiniSerializer(read_only=True)
    stay_type = serializers.SerializerMethodField()                # ★ stay_type も返す

    class Meta:
        model  = CastPayout
        fields = ('id', 'amount', 'cast', 'bill', 'bill_item', 'stay_type')

    def get_stay_type(self, obj):
        # 伝票内でそのキャストの最新 stay を見る
        s = obj.bill.stays.filter(cast_id=obj.cast_id).order_by('-entered_at').first()
        return getattr(s, 'stay_type', None)

class CastPayrollSummaryRowSerializer(serializers.Serializer):
    id          = serializers.IntegerField()
    stage_name  = serializers.CharField()
    worked_min  = serializers.IntegerField()
    total_hours = serializers.FloatField()
    hourly_pay  = serializers.IntegerField()
    commission  = serializers.IntegerField()
    total       = serializers.IntegerField()


# ═══════════════════════════════════════════════════════════════════
# 時間別売上サマリ用シリアライザ
# ═══════════════════════════════════════════════════════════════════
from .models import HourlySalesSummary, HourlyCastSales

class HourlyCastSalesSerializer(serializers.ModelSerializer):
    """時間別キャスト売上（内訳）"""
    cast = CastMiniSerializer(read_only=True)
    
    class Meta:
        model = HourlyCastSales
        fields = (
            'cast', 'sales_total', 'sales_nom', 'sales_in', 'sales_free',
            'sales_champagne', 'bill_count'
        )


class HourlySalesSummarySerializer(serializers.ModelSerializer):
    """時間別売上サマリ（キャスト内訳付き）"""
    cast_breakdown = HourlyCastSalesSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    business_hours_display = serializers.CharField(source='store.business_hours_display', read_only=True)
    is_within_business_hours = serializers.BooleanField(read_only=True)
    time_display = serializers.SerializerMethodField()
    
    class Meta:
        model = HourlySalesSummary
        fields = (
            'id', 'store', 'store_name', 'date', 'hour', 'time_display',
            'sales_total', 'bill_count', 'customer_count',
            'sales_set', 'sales_drink', 'sales_food', 'sales_champagne',
            'cast_breakdown', 'is_within_business_hours', 'business_hours_display',
            'updated_at'
        )
    
    def get_time_display(self, obj):
        """時刻を HH:00 フォーマットで返す"""
        return f"{obj.hour:02d}:00"

