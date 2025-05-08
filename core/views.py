from rest_framework import viewsets, permissions
from .models import (
    Store, Rank, Course, RankCourse, Option, GroupOptionPrice,
    Cast, CastCoursePrice, CastOption, Driver, Customer,
    Reservation
)
from .serializers import (
    StoreSerializer, RankSerializer, CourseSerializer, RankCourseSerializer,
    OptionSerializer, GroupOptionPriceSerializer,
    CastSerializer, CastCoursePriceSerializer, CastOptionSerializer,
    DriverSerializer, CustomerSerializer, ReservationSerializer
)

# ---- 基本 read/write 権限は STAFF。調整は後で ----
class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser or request.user.groups.filter(name='STAFF').exists()

# ---------- マスタ ----------
class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsStaff]

class RankViewSet(viewsets.ModelViewSet):
    queryset = Rank.objects.all()
    serializer_class = RankSerializer
    permission_classes = [IsStaff]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsStaff]

class RankCourseViewSet(viewsets.ModelViewSet):
    queryset = RankCourse.objects.select_related('store','rank','course')
    serializer_class = RankCourseSerializer
    permission_classes = [IsStaff]

class OptionViewSet(viewsets.ModelViewSet):
    queryset = Option.objects.all()
    serializer_class = OptionSerializer
    permission_classes = [IsStaff]

class GroupOptionPriceViewSet(viewsets.ModelViewSet):
    queryset = GroupOptionPrice.objects.select_related('store','course')
    serializer_class = GroupOptionPriceSerializer
    permission_classes = [IsStaff]

# ---------- キャスト ----------
class CastViewSet(viewsets.ModelViewSet):
    queryset = Cast.objects.select_related('store','rank')
    serializer_class = CastSerializer
    permission_classes = [IsStaff]

class CastCoursePriceViewSet(viewsets.ModelViewSet):
    queryset = CastCoursePrice.objects.select_related('cast','course')
    serializer_class = CastCoursePriceSerializer
    permission_classes = [IsStaff]

class CastOptionViewSet(viewsets.ModelViewSet):
    queryset = CastOption.objects.select_related('cast','option')
    serializer_class = CastOptionSerializer
    permission_classes = [IsStaff]

# ---------- 顧客・ドライバー ----------
class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.select_related('user','store')
    serializer_class = DriverSerializer
    permission_classes = [IsStaff]

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsStaff]

# ---------- 予約 ----------
class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related(
        'store', 'driver', 'customer'
    ).prefetch_related('casts', 'charges')
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
