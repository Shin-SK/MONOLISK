from rest_framework import serializers
from .models import (
    Store, Rank, Course, RankCourse, Option, GroupOptionPrice,
    Cast, CastCoursePrice, CastOption, Driver, Customer,
    Reservation, ReservationCast, ReservationCharge, CashFlow
)

# ---------- マスタ ----------
class StoreSerializer(serializers.ModelSerializer):
    class Meta: model = Store; fields = '__all__'

class RankSerializer(serializers.ModelSerializer):
    class Meta: model = Rank; fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    class Meta: model = Course; fields = '__all__'

class RankCourseSerializer(serializers.ModelSerializer):
    class Meta: model = RankCourse; fields = '__all__'

class OptionSerializer(serializers.ModelSerializer):
    class Meta: model = Option; fields = '__all__'

class GroupOptionPriceSerializer(serializers.ModelSerializer):
    class Meta: model = GroupOptionPrice; fields = '__all__'

# ---------- キャスト ----------
class CastSerializer(serializers.ModelSerializer):
    class Meta: model = Cast; fields = '__all__'

class CastCoursePriceSerializer(serializers.ModelSerializer):
    class Meta: model = CastCoursePrice; fields = '__all__'

class CastOptionSerializer(serializers.ModelSerializer):
    class Meta: model = CastOption; fields = '__all__'

# ---------- 顧客・ドライバー ----------
class DriverSerializer(serializers.ModelSerializer):
    class Meta: model = Driver; fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    class Meta: model = Customer; fields = '__all__'

# ---------- 予約周り（ネスト用） ----------
class ReservationCastSerializer(serializers.ModelSerializer):
    class Meta: model = ReservationCast; fields = '__all__'

class ReservationChargeSerializer(serializers.ModelSerializer):
    class Meta: model = ReservationCharge; fields = '__all__'

class CashFlowSerializer(serializers.ModelSerializer):
    class Meta: model = CashFlow; fields = '__all__'

# ---------- 予約メイン ----------
class ReservationSerializer(serializers.ModelSerializer):
    casts   = ReservationCastSerializer(many=True, read_only=True)
    charges = ReservationChargeSerializer(many=True, read_only=True)
    expected_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Reservation
        fields = '__all__'
