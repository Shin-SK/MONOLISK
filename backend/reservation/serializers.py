from rest_framework import serializers
from .models import Reservation, Course, Menu, Discount
from account.models import Store, CustomUser
from account.serializers import CastWithNicknamesSerializer

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name"]

class CastSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "full_name"]

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "full_name"]

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

class ReservationSerializer(serializers.ModelSerializer):
    course = CourseSerializer()
    menus = MenuSerializer(many=True)
    store = StoreSerializer()
    cast = CastWithNicknamesSerializer()
    driver = DriverSerializer()
    cast_received = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    driver_received = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    store_received = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = Reservation
        fields = [
            "id", "customer_name", "start_time", "course", "menus", "store", "cast", "driver",
            "membership_type", "time_minutes", "reservation_amount", "discounts",
            "enrollment_fee", "enrollment_fee_discounted",
            "photo_nomination_fee", "photo_nomination_fee_discounted",
            "regular_nomination_fee", "regular_nomination_fee_discounted",
            "cast_received", "driver_received", "store_received"
        ]


# reservations/serializers.py
class ReservationCreateSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), allow_null=True)
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), allow_null=True)
    cast = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(role='cast'), allow_null=True)
    driver = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(role='driver'), allow_null=True)
    menus = serializers.PrimaryKeyRelatedField(queryset=Menu.objects.all(), many=True, required=False)
    discounts = serializers.PrimaryKeyRelatedField(queryset=Discount.objects.all(), many=True, required=False)
    
    # これらは計算フィールドなので書き込み対象外
    reservation_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cast_received = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    driver_received = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    store_received = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "customer_name", "start_time", "course", "menus", "store", "cast", "driver",
            "membership_type", "time_minutes", "reservation_amount", "discounts",
            "enrollment_fee", "enrollment_fee_discounted",
            "photo_nomination_fee", "photo_nomination_fee_discounted",
            "regular_nomination_fee", "regular_nomination_fee_discounted",
            "cast_received", "driver_received", "store_received"
        ]

    def create(self, validated_data):
        # 除外すべきフィールドが万が一含まれていたら取り除く
        validated_data.pop('reservation_amount', None)
        validated_data.pop('cast_received', None)
        validated_data.pop('driver_received', None)
        validated_data.pop('store_received', None)
        return super().create(validated_data)
