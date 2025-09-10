# billing/serializer.py
from rest_framework import serializers
from .models import Store, Table, Bill, ItemMaster, BillItem, CastPayout, BillCastStay, Cast, ItemCategory, CastCategoryRate, CastShift, CastDailySummary, Staff, StaffShift, Customer, CustomerLog
from dj_rest_auth.serializers import UserDetailsSerializer
from .models import User
from cloudinary.utils import cloudinary_url
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from datetime import date
from .services import sync_nomination_fees
from django.templatetags.static import static
from django.utils import timezone


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model    = Store
        fields    = '__all__'


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model    = Table
        fields    = '__all__'


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
                  'table']
        
class TableMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Table
        fields = ['number']
        


class CastItemDetailSerializer(serializers.ModelSerializer):
    bill_id    = serializers.IntegerField(source='bill.id', read_only=True)
    closed_at  = serializers.DateTimeField(source='bill.closed_at', read_only=True)
    table_no   = serializers.IntegerField(source='bill.table.number', read_only=True)
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


class TableMiniSerializer(serializers.ModelSerializer):
    store = serializers.IntegerField(source='store.id', read_only=True)   # ★追加
    class Meta:
        model  = Table
        fields = ('id', 'number', 'store')


class BillCastStayMini(serializers.ModelSerializer):
    class Meta:
        model  = BillCastStay
        fields = ('cast',)           # cast は {id, stage_name} で返る

class BillCastStayMiniSerializer(serializers.ModelSerializer):
    cast_id = serializers.PrimaryKeyRelatedField(
        source='cast', queryset=Cast.objects.all(), write_only=True
    )

    def create(self, vd):
        if vd.get('stay_type') == 'nom' and 'is_honshimei' not in vd:
            vd['is_honshimei'] = True
        return super().create(vd)

    def update(self, inst, vd):
        st = vd.get('stay_type', inst.stay_type)
        if st == 'nom' and vd.get('is_honshimei') is None:
            vd['is_honshimei'] = True
        return super().update(inst, vd)

    class Meta:
        model  = BillCastStay
        fields = ('id', 'cast_id', 'stay_type', 'is_honshimei', 'entered_at', 'left_at')
        read_only_fields = ('entered_at', 'left_at')


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

    class Meta:
        model  = CastPayout
        fields = ('id', 'amount', 'bill', 'bill_item', 'cast')

    def get_bill(self, obj):
        if obj.bill is None:                # ← ★ null セーフ
            return None
        return {
            'id'       : obj.bill_id,
            'closed_at': obj.bill.closed_at,
        }
  


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


class CastCategoryRateSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(  # “set”“drink”… の code
        slug_field='code', queryset=ItemCategory.objects.all()
    )

    class Meta:
        model  = CastCategoryRate
        fields = ('id', 'category', 'rate_free',
                  'rate_nomination', 'rate_inhouse')
  


User = get_user_model()

class CastSerializer(serializers.ModelSerializer):
    # ---------- 店が入力・更新できる write‑only フィールド ----------
    username    = serializers.CharField(write_only=True, required=True)
    first_name  = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name   = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # ---------- 取得時に返す read‑only フィールド ----------
    username_read   = serializers.CharField(source='user.username',   read_only=True)
    first_name_read = serializers.CharField(source='user.first_name', read_only=True)
    last_name_read  = serializers.CharField(source='user.last_name',  read_only=True)

    avatar_url = serializers.SerializerMethodField()
    category_rates = CastCategoryRateSerializer(many=True, required=False)
    store = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        required=False, write_only=True,
    )
    hourly_wage = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model  = Cast
        fields = (
            "id", "stage_name", "store",
            # ← ここから User 関連
            "username", "username_read",
            "first_name", "first_name_read",
            "last_name",  "last_name_read",
            "hourly_wage",
            # ← バック率
            "back_rate_free_override",
            "back_rate_nomination_override",
            "back_rate_inhouse_override",
            # ← 画像
            "avatar", "avatar_url",
            'category_rates',
        )

    # ---------- helper ----------
    def get_avatar_url(self, obj):
        if obj.avatar:
            return cloudinary_url(obj.avatar.public_id,
                                  format=obj.avatar.format,
                                  secure=True)[0]
        return None


    # --------------------------------------------------
    #                     CREATE
    # --------------------------------------------------
    def create(self, validated_data):
        # ネストされて来た rate を取り出す
        rates_data = validated_data.pop('category_rates', [])

        # まずユーザーを作る（既存ロジックはそのまま）
        username   = validated_data.pop('username')
        first_name = validated_data.pop('first_name', '')
        last_name  = validated_data.pop('last_name', '')

        request = self.context.get('request')
        if not validated_data.get('store') and request and request.user.store_id:
            validated_data['store'] = request.user.store

        user = User.objects.create_user(
            username=username,
            password=get_random_string(12),
            first_name=first_name,
            last_name=last_name,
        )

        # Cast 本体を作成
        cast = Cast.objects.create(user=user, **validated_data)


        # 新規入店の子につける0サマリー
        CastDailySummary.objects.get_or_create(
            cast=cast,
            store=cast.store,          # 同じ店舗で
            work_date=date.today(),    # 今日の日付
            defaults=dict(
                worked_min   = 0,
                payroll      = 0,
                sales_free   = 0,
                sales_in     = 0,
                sales_nom    = 0,
                sales_champ  = 0,
            )
        )

        # rate 行を同期
        self._sync_rates(cast, rates_data)
        return cast

    # --------------------------------------------------
    #                     UPDATE
    # --------------------------------------------------
    def update(self, instance, validated_data):
        # rate が来た場合だけ処理。来なければ据え置き
        rates_data = validated_data.pop('category_rates', None)

        # ユーザー情報更新（既存ロジック）
        user = instance.user
        if 'username' in validated_data:
            user.username = validated_data.pop('username')
        if 'first_name' in validated_data:
            user.first_name = validated_data.pop('first_name')
        if 'last_name' in validated_data:
            user.last_name = validated_data.pop('last_name')
        user.save(update_fields=['username', 'first_name', 'last_name'])

        # Cast 本体フィールドを更新
        cast = super().update(instance, validated_data)

        # rate を送り直してきた場合だけ入れ替え
        if rates_data is not None:
            self._sync_rates(cast, rates_data)

        return cast

    # --------------------------------------------------
    #            category‑rate 同期ヘルパ
    # --------------------------------------------------
    def _sync_rates(self, cast, rates_data):
        """
        シンプルに：
        1. 既存行を全削除 → 2. 送られてきた行を丸ごと作り直し
        """
        CastCategoryRate.objects.filter(cast=cast).delete()
        for r in rates_data:
            CastCategoryRate.objects.create(cast=cast, **r)



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
    cast = CastMiniSerializer()
    class Meta:
        model  = BillCastStay
        fields = ("cast", "stay_type", "is_honshimei", "entered_at", "left_at")



class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = '__all__'       # 気になるなら explicit に並べる
        read_only_fields = ('last_drink', 'last_cast', 'created_at', 'updated_at')

class CustomerLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model  = CustomerLog
        fields = ('id', 'action', 'user_name', 'payload', 'at')



class BillSerializer(serializers.ModelSerializer):
    table        = TableMiniSerializer(read_only=True)     # ネスト表示用
    items        = BillItemSerializer(read_only=True, many=True)
    stays        = BillCastStaySerializer(read_only=True, many=True)
    subtotal     = serializers.SerializerMethodField()
    service_charge = serializers.SerializerMethodField()
    tax          = serializers.SerializerMethodField()
    grand_total  = serializers.SerializerMethodField()
    inhouse_casts = CastSerializer(many=True, read_only=True)
    opened_at     = serializers.DateTimeField(required=False, allow_null=True)
    expected_out  = serializers.DateTimeField(required=False, allow_null=True)
    set_rounds   = serializers.IntegerField(read_only=True)
    ext_minutes  = serializers.IntegerField(read_only=True)
    main_cast      = serializers.PrimaryKeyRelatedField(
        queryset=Cast.objects.all(), allow_null=True, required=False
    )
    main_cast_obj  = CastMiniSerializer(source='main_cast', read_only=True)
    customer_ids = serializers.PrimaryKeyRelatedField(
        source='customers', many=True,
        queryset=Customer.objects.all(),
        required=False, write_only=True
    )
    customers = CustomerSerializer(many=True, read_only=True)
    customer_display_name = serializers.SerializerMethodField()
    # ---------- WRITE ----------
    # “卓番号” を受け取る専用フィールド
    table_id = serializers.PrimaryKeyRelatedField(
        source='table',                # ← Bill.table へマッピング
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
    change_due  = serializers.SerializerMethodField()
    paid_total  = serializers.IntegerField(read_only=True)


    class Meta:
        model = Bill
        fields = (
            # ---- 基本 ----
            "id", "table", "table_id", "opened_at", "closed_at",
            # ---- 金額 ----
            "subtotal", "service_charge", "tax", "grand_total", "total",
            "paid_cash","paid_card","paid_total","change_due",
            # ---- 関連 ----
            "items", "stays","expected_out",
            "nominated_casts", "settled_total",
            "inhouse_casts",        # READ
            "inhouse_casts_w",      # WRITE
            "free_ids","set_rounds","ext_minutes", 'main_cast',      # WRITE 用 (id)
            'main_cast_obj',  # READ 用 ({id,stage_name})
            'customers',      # READ
            'customer_ids',   # WRITE
            'customer_display_name',
        )
        read_only_fields = (
            "subtotal", "service_charge", "tax", "grand_total", "total",
            "closed_at", "settled_total","set_rounds","ext_minutes",
            "paid_total","change_due",
        )
        depth = 2

    def get_change_due(self, obj):
        st = obj.settled_total if obj.settled_total is not None else obj.grand_total
        st = st or 0
        return max(0, obj.paid_total - st)

    # ───────── 顧客情報取得 ──────────
    # 先頭 1 名だけバッジに出す用途
    def get_customer_display_name(self, obj):
        first = obj.customers.first()
        return first.display_name if first else ''
    
    
    def to_representation(self, obj):
        rep = super().to_representation(obj)
        # 先頭 1 件だけ代表名を返す
        first = obj.customers.first()
        rep['customer_display_name'] = first.display_name if first else ''
        return rep

    # ───────── READ helpers ──────────
    def get_inhouse_casts(self, obj):
        return list(
            obj.stays.filter(stay_type="in")
               .values_list("cast_id", flat=True)
        )

    # --------------------------------------------------
    #                 CREATE
    # --------------------------------------------------
    def create(self, validated_data):
        if validated_data.get('opened_at') is None:
            validated_data['opened_at'] = timezone.now()
        nominated = validated_data.pop("nominated_casts", [])
        inhouse   = validated_data.pop("inhouse_casts_w", [])
        bill = Bill.objects.create(**validated_data)
        if nominated:
            bill.nominated_casts.set(nominated)

        # ↑ stay 行を追加するロジックをここで呼ぶ場合は
        #    その直後に sync_nomination_fees() を実行
        sync_nomination_fees(
            bill,
            prev_main=set(),              # before = 0
            new_main=set(nominated),      # after  = 指名キャスト
            prev_in=set(),
            new_in=set(inhouse),
        )
        return bill

    # --------------------------------------------------
    #                 UPDATE
    # --------------------------------------------------
    # billing/serializers.py  ── BillSerializer.update

    def update(self, instance, validated_data):
        # ---------- 0) 更新前スナップショット（ここが最重要） ----------
        prev_main = set(instance.nominated_casts.values_list("id", flat=True))
        prev_in   = set(
            instance.stays.filter(stay_type="in", left_at__isnull=True)
                .values_list("cast_id", flat=True)
        )

        # ---------- 1) M2M/配列系は validated_data から先に抜く ----------
        cust_ids       = validated_data.pop('customer_ids', None)
        nominated_raw  = validated_data.pop("nominated_casts", None)
        inhouse_raw    = validated_data.pop("inhouse_casts_w", None)
        free_raw       = validated_data.pop("free_ids", None)

        # ---------- 2) 通常フィールドだけ parent で更新（※1回だけ） ----------
        instance = super().update(instance, validated_data)

        # 顧客 M2M
        if cust_ids is not None:
            instance.customers.set(cust_ids)

        # ユーティリティ
        to_ids = lambda raw: [c.id if isinstance(c, Cast) else c for c in (raw or [])]
        nominated_ids = to_ids(nominated_raw)
        inhouse_ids   = to_ids(inhouse_raw)
        free_ids_orig = to_ids(free_raw)

        # 既存 stay をキャッシュ
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
                        entered_at=timezone.now(),
                        stay_type="nom",
                        is_honshimei=True,
                    )
                else:
                    stay.stay_type = "nom"
                    stay.left_at   = None
                    upd = ["stay_type", "left_at"]
                    if not stay.is_honshimei:
                        stay.is_honshimei = True
                        upd.append("is_honshimei")
                    stay.save(update_fields=upd)

            for cid, stay in stay_map.items():
                if cid not in nominated_ids and stay.stay_type == "nom":
                    stay.stay_type = "in" if cid in inhouse_ids else "free"
                    upd = ["stay_type"]
                    if stay.is_honshimei:
                        stay.is_honshimei = False
                        upd.append("is_honshimei")
                    stay.save(update_fields=upd)

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
            free_ids = [cid for cid in free_ids_orig if cid not in inhouse_ids and cid not in nominated_ids]
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

            active_free = instance.stays.filter(stay_type="free", left_at__isnull=True)
            for stay in active_free:
                if stay.cast_id not in free_ids:
                    stay.left_at = timezone.now()
                    stay.save(update_fields=["left_at"])

        # ---------- 3) 更新後スナップショット ----------
        new_main = set(instance.nominated_casts.values_list('id', flat=True))
        new_in   = set(
            instance.stays.filter(stay_type='in', left_at__isnull=True)
                    .values_list('cast_id', flat=True)
        )

        # ---------- 4) 料金行を差分同期 ----------
        sync_nomination_fees(instance, prev_main, new_main, prev_in, new_in)
        return instance




    def _store_rates(self, obj):
        """DEPRECATED: 計算は BillCalculator に統合済み。"""
        return Decimal("0"), Decimal("0")

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_service_charge(self, obj):
        return obj.service_charge

    def get_tax(self, obj):
        return obj.tax

    def get_grand_total(self, obj):
        return obj.total or obj.grand_total


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


class CastMiniSerializer(serializers.ModelSerializer):
    """最小限だけ返すネスト用"""
    class Meta:
        model  = Cast
        fields = ('id', 'stage_name')

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
            obj.payroll
            + obj.sales_free
            + obj.sales_in
            + obj.sales_nom
            + obj.sales_champ
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
    # 既存の user → username に分解
    username    = serializers.CharField(source='user.username',   read_only=True)
    first_name  = serializers.CharField(source='user.first_name', read_only=True)
    last_name   = serializers.CharField(source='user.last_name',  read_only=True)
    full_name   = serializers.SerializerMethodField()

    stores      = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True
    )

    # ① 内部コード＝write-only
    role       = serializers.ChoiceField(
        choices=Staff.ROLE_CHOICES,
        write_only=True, required=False
    )
    # ② 表示用ラベル＝read-only
    role_label = serializers.CharField(
        source='get_role_display',
        read_only=True
    )
    role_code = serializers.CharField(
        source='role',
        read_only=True
    )


    class Meta:
        model  = Staff
        fields = (
            'id', 'username', 'first_name', 'last_name',
            'full_name', 'hourly_wage', 'stores', 'role','role_label','role_code',
        )

    def get_full_name(self, obj):
        fn = (obj.user.first_name + obj.user.last_name).strip()
        return fn or obj.user.username


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
            return obj.bill_item.bill.table.number
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
            return obj.bill_item.bill.table.number
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
