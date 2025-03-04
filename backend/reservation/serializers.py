from rest_framework import serializers
from .models import Reservation, Course, Menu, Discount, StorePricing
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

class StorePricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorePricing
        fields = ["id", "store", "course", "time_minutes", "price"]

class ReservationSerializer(serializers.ModelSerializer):
    """
    予約の読み取り専用シリアライザ (GET時用)
    例: 一覧や詳細を返す
    """
    course = CourseSerializer(required=False, allow_null=True)
    menus = MenuSerializer(many=True, required=False)
    store = serializers.SerializerMethodField()
    cast = serializers.SerializerMethodField()
    driver = serializers.SerializerMethodField()
    store_user = serializers.SerializerMethodField()
    discounts = DiscountSerializer(many=True, required=False)

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
            "regular_nomination_fee_discounted"
        ]

    def get_store(self, obj):
        if obj.store:
            return {"id": obj.store.id, "name": obj.store.name}
        return None

    def get_cast(self, obj):
        if obj.cast:
            return {"id": obj.cast.id, "full_name": obj.cast.full_name}
        return None

    def get_driver(self, obj):
        if obj.driver:
            return {"id": obj.driver.id, "full_name": obj.driver.full_name}
        return None

    def get_store_user(self, obj):
        if obj.store_user:
            return {
                "id": obj.store_user.id,
                "nickname": obj.store_user.nickname
            }
        return None

class ReservationCreateSerializer(serializers.ModelSerializer):
    """
    新規作成/更新用シリアライザ (POST/PUT用)
    モデルのすべてのフィールドを列挙し、
    フロントが送ってくるフィールドをすべて書き込みできるようにする。
    """

    # 外部キー関連: driver, store_user, cast, store, course など
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

    # 多対多: menus, discounts
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
    membership_type = serializers.CharField(required=False, allow_blank=True)
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
            "regular_nomination_fee_discounted"
        ]

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
