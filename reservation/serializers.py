from rest_framework import serializers
from .models import Reservation, Course, Menu, Discount
from account.models import StoreUser, CustomUser, Store

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "name", "price"]

class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = ["id", "name", "price"]

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ["id", "name", "amount"]


#######################
# 読み取り専用 (GET用) #
#######################
class ReservationSerializer(serializers.ModelSerializer):
    """
    GET時（一覧/詳細）の読み取り専用
    """

    course = CourseSerializer(required=False)
    menus = MenuSerializer(many=True, required=False)
    store = serializers.SerializerMethodField()
    cast = serializers.SerializerMethodField()
    driver = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id",
            "customer_name",
            "start_time",
            "course",
            "menus",
            "store",
            "cast",
            "driver",
            "store_user",        # 直接表示してもいいし get_store_user()にしてもいい
            "cast_received",
            "driver_received",
            "store_received",
            "membership_type",
            "time_minutes",
            "reservation_amount",
            "discounts",
            "enrollment_fee",
            "enrollment_fee_discounted",
            "photo_nomination_fee",
            "photo_nomination_fee_discounted",
            "regular_nomination_fee",
            "regular_nomination_fee_discounted",
            "postal_code",
            "address",
        ]


    def get_cast(self, obj):
        if not obj.cast:
            return None

        cast_dict = {
            "id": obj.cast.id,
            "full_name": obj.cast.full_name
        }
        store_user = StoreUser.objects.filter(user=obj.cast, store=obj.store).first()

        if store_user and store_user.cast_photo:
            # まずは相対パス（またはCloudinaryのURL）を取得
            relative_or_cloudinary_url = store_user.cast_photo.url

            # request コンテキストから絶対URLに変換
            request = self.context.get("request")
            if request:
                cast_dict["cast_photo"] = request.build_absolute_uri(relative_or_cloudinary_url)
            else:
                cast_dict["cast_photo"] = relative_or_cloudinary_url
        else:
            cast_dict["cast_photo"] = None

        return cast_dict


    def get_store(self, obj):
        if obj.store:
            return {"id": obj.store.id, "name": obj.store.name}
        return None

    def get_driver(self, obj):
        if obj.driver:
            return {"id": obj.driver.id, "full_name": obj.driver.full_name}
        return None


###############################
# 新規作成 / 更新 (POST/PUT用) #
###############################
class ReservationCreateSerializer(serializers.ModelSerializer):
    """
    予約を新規作成/更新する際に使用するシリアライザ。
    モデルの全フィールドを列挙し、
    フロントが送ってくるデータに対応させる。
    """

    # 外部キー関連
    driver = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role='driver'),
        required=False,
        allow_null=True
    )
    store_user = serializers.PrimaryKeyRelatedField(
        queryset=StoreUser.objects.all(),
        required=False,
        allow_null=True
    )
    cast = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role='cast'),
        required=False,
        allow_null=True
    )
    store = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        required=False,
        allow_null=True
    )
    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        required=False,
        allow_null=True
    )

    # 多対多
    menus = serializers.PrimaryKeyRelatedField(
        queryset=Menu.objects.all(),
        many=True,
        required=False
    )
    discounts = serializers.PrimaryKeyRelatedField(
        queryset=Discount.objects.all(),
        many=True,
        required=False
    )

    # Decimal / Boolean / Char fields
    cast_received = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, allow_null=True
    )
    driver_received = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, allow_null=True
    )
    store_received = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, allow_null=True
    )
    membership_type = serializers.CharField(required=False)
    reservation_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, allow_null=True
    )
    enrollment_fee = serializers.BooleanField(required=False)
    enrollment_fee_discounted = serializers.BooleanField(required=False)
    photo_nomination_fee = serializers.BooleanField(required=False)
    photo_nomination_fee_discounted = serializers.BooleanField(required=False)
    regular_nomination_fee = serializers.BooleanField(required=False)
    regular_nomination_fee_discounted = serializers.BooleanField(required=False)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "customer_name",
            "start_time",
            "course",
            "menus",
            "store",
            "cast",
            "driver",
            "store_user",
            "cast_received",
            "driver_received",
            "store_received",
            "membership_type",
            "time_minutes",
            "reservation_amount",
            "discounts",
            "enrollment_fee",
            "enrollment_fee_discounted",
            "photo_nomination_fee",
            "photo_nomination_fee_discounted",
            "regular_nomination_fee",
            "regular_nomination_fee_discounted",
            "postal_code",
            "address",
        ]

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
