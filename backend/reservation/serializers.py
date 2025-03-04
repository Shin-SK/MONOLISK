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
    """
    詳細表示用の読み取りSerializer
    """
    course = CourseSerializer()
    menus = MenuSerializer(many=True)
    store = StoreSerializer()
    cast = CastWithNicknamesSerializer()
    driver = DriverSerializer()

    # 予約済みデータの参照時用: 読み取りのみ（フロントで再計算 or 手動修正したければ別APIを使う想定）
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

class ReservationCreateSerializer(serializers.ModelSerializer):
    """
    新規作成/更新時用のSerializer
    フロント側で計算した値をそのまま書き込めるように read_only を外す。
    """
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), allow_null=True)
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), allow_null=True)
    cast = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(role='cast'), allow_null=True)
    driver = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(role='driver'), allow_null=True)
    menus = serializers.PrimaryKeyRelatedField(queryset=Menu.objects.all(), many=True, required=False)
    discounts = serializers.PrimaryKeyRelatedField(queryset=Discount.objects.all(), many=True, required=False)
    
    # フロント計算の結果を受け取って保存するために read_only を外す。
    reservation_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    cast_received = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    driver_received = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    store_received = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

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
        # 以前は読み取り専用にしていた項目をpopしていたが、今回は保存するのでそのまま
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # 更新時も同様に、そのまま上書き保存する
        return super().update(instance, validated_data)
