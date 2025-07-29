# billing/serializer.py
from rest_framework import serializers
from .models import Store, Table, Bill, ItemMaster, BillItem, CastPayout, BillCastStay, Cast, ItemCategory, CastCategoryRate, CastShift, CastDailySummary
from django.utils import timezone
from dj_rest_auth.serializers import UserDetailsSerializer
from .models import User
from cloudinary.utils import cloudinary_url
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string


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
  
class CastSalesSummarySerializer(serializers.Serializer):
    cast_id      = serializers.IntegerField()
    stage_name   = serializers.CharField()          # ← フィールド名変更
    sales_nom    = serializers.IntegerField()
    sales_in     = serializers.IntegerField()
    sales_free   = serializers.IntegerField()
    sales_champ  = serializers.IntegerField()
    total        = serializers.IntegerField()


class BillItemMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BillItem
        fields = ['id', 'name', 'qty', 'price', 'is_nomination',
                  'is_inhouse', 'exclude_from_payout']


class BillMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Bill
        fields = ['id', 'opened_at', 'closed_at',               # ← opened_at を追加
                  'grand_total','subtotal','table',                                # ← 伝票の総額
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
    amount     = serializers.SerializerMethodField()   # ギャラ

    class Meta:
        model  = BillItem
        fields = (
            'id', 'closed_at', 'bill_id', 'table_no',
            'name', 'qty', 'subtotal', 'back_rate', 'amount',
            'is_nomination', 'is_inhouse', 
        )

    def get_subtotal(self, obj): return obj.subtotal
    def get_back_rate(self, obj): return float(obj.back_rate)
    def get_amount(self, obj):
        return int(obj.subtotal * obj.back_rate)


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

    class Meta:                         # ★←欠けていた
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
        fields = ('cast',)           # cast は {id, stage_name} で返る



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
  

class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = ItemCategory
        fields = ("code", "name")     # これだけで OK



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
        if not validated_data.get('store') and request and hasattr(request.user, 'store_profile'):
            validated_data['store'] = request.user.store_profile.store

        user = User.objects.create_user(
            username=username,
            password=get_random_string(12),
            first_name=first_name,
            last_name=last_name,
        )

        # Cast 本体を作成
        cast = Cast.objects.create(user=user, **validated_data)

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
    cast = CastMiniSerializer()                   # ← ネストに置き換え

    class Meta:
        model  = BillCastStay
        fields = ("cast", "entered_at", "left_at", "stay_type")


class BillSerializer(serializers.ModelSerializer):
    # ---------- READ ----------
    table        = TableMiniSerializer(read_only=True)     # ネスト表示用
    items        = BillItemSerializer(read_only=True, many=True)
    stays        = BillCastStaySerializer(read_only=True, many=True)
    subtotal     = serializers.SerializerMethodField()
    service_charge = serializers.SerializerMethodField()
    tax          = serializers.SerializerMethodField()
    grand_total  = serializers.SerializerMethodField()
    inhouse_casts = CastSerializer(many=True, read_only=True)
    expected_out = serializers.DateTimeField(read_only=True)
    set_rounds   = serializers.IntegerField(read_only=True)
    ext_minutes  = serializers.IntegerField(read_only=True)
    main_cast      = serializers.PrimaryKeyRelatedField(
        queryset=Cast.objects.all(), allow_null=True, required=False
    )
    main_cast_obj  = CastMiniSerializer(source='main_cast', read_only=True)
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
            "inhouse_casts",        # READ
            "inhouse_casts_w",      # WRITE
            "free_ids","set_rounds","ext_minutes", 'main_cast',      # WRITE 用 (id)
            'main_cast_obj',  # READ 用 ({id,stage_name})
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
    #                 CREATE
    # --------------------------------------------------
    def create(self, validated_data):
        nominated = validated_data.pop("nominated_casts", [])
        bill = Bill.objects.create(**validated_data)   # table もここでセットされる
        if nominated:
            bill.nominated_casts.set(nominated)
        return bill

    # --------------------------------------------------
    #                 UPDATE
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
        svc      = self.get_service_charge(obj)
        _, tr    = self._store_rates(obj)
        return round((subtotal + svc) * tr)

    def get_grand_total(self, obj):
        return obj.total or (
            self.get_subtotal(obj) +
            self.get_service_charge(obj) +
            self.get_tax(obj)
        )



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


class CastRankingSerializer(serializers.Serializer):
    cast_id    = serializers.IntegerField()
    stage_name = serializers.CharField()
    revenue    = serializers.IntegerField()