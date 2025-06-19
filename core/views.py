#veiws.py
from rest_framework import viewsets, permissions ,filters, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .filters import CustomerFilter
from rest_framework.decorators import action

from .models import (
    Store, Rank, Course, RankCourse, Option, GroupOptionPrice,
    CastProfile, CastCoursePrice, CastOption, Driver, Customer,
    Reservation, ReservationCast
)
from .serializers import (
    StoreSerializer, RankSerializer, CourseSerializer, RankCourseSerializer,
    OptionSerializer, GroupOptionPriceSerializer,
    CastSerializer, CastCoursePriceSerializer, CastOptionSerializer,
    DriverSerializer, CustomerSerializer, ReservationSerializer, DriverListSerializer,  
)
from.filters import ReservationFilter



# ---- 基本 read/write 権限は STAFF。調整は後で ----
class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser or request.user.groups.filter(name='STAFF').exists()

# ---------- マスタ ----------
class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [AllowAny]

class RankViewSet(viewsets.ModelViewSet):
    queryset = Rank.objects.all()
    serializer_class = RankSerializer
    permission_classes = [AllowAny]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

class RankCourseViewSet(viewsets.ModelViewSet):
    queryset = RankCourse.objects.select_related('store','rank','course')
    serializer_class = RankCourseSerializer
    permission_classes = [AllowAny]

class OptionViewSet(viewsets.ModelViewSet):
    queryset = Option.objects.all()
    serializer_class = OptionSerializer
    permission_classes = [AllowAny]

class GroupOptionPriceViewSet(viewsets.ModelViewSet):
    queryset = GroupOptionPrice.objects.select_related('store','course')
    serializer_class = GroupOptionPriceSerializer
    permission_classes = [AllowAny]

# ---------- キャスト ----------
class CastViewSet(viewsets.ModelViewSet):
    queryset = CastProfile.objects.select_related('store','rank')
    serializer_class = CastSerializer
    permission_classes = [AllowAny]

class CastCoursePriceViewSet(viewsets.ModelViewSet):
    queryset = CastCoursePrice.objects.select_related('cast','course')
    serializer_class = CastCoursePriceSerializer
    permission_classes = [AllowAny]

class CastOptionViewSet(viewsets.ModelViewSet):
    queryset = CastOption.objects.select_related('option')
    serializer_class = CastOptionSerializer
    permission_classes = [permissions.IsAdminUser]   # STAFF のみに変更したければ
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cast_profile']


# ---------- 顧客・ドライバー ----------
class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.select_related("user", "store")
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.query_params.get("simple") == "1":
            return DriverListSerializer
        return DriverSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class    = CustomerFilter

# ---------- 予約 ----------


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related(
        "store", "driver", "customer"
    ).prefetch_related("casts", "charges")
    serializer_class    = ReservationSerializer
    permission_classes  = [AllowAny]
    pagination_class    = None      # ← 必要なら外して OK
    filter_backends    = [DjangoFilterBackend]
    filterset_class    = ReservationFilter

    # ------- 共通ヘルパ -------
    def _sync_casts(self, reservation, casts_data):
        """
        受け取った casts 配列で ReservationCast 行を置き換える
        """
        ReservationCast.objects.filter(reservation=reservation).delete()
        objs = [
            ReservationCast(
                reservation    = reservation,
                cast_profile_id= c["cast_profile"],
                rank_course_id = c["rank_course"],
            )
            for c in casts_data
        ]
        ReservationCast.objects.bulk_create(objs)


    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        if not request.user.groups.filter(name='CAST').exists():
            return Response(status=403)
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.filter(casts__cast_profile__user=request.user)
        date = request.query_params.get('date')
        if date:
            qs = qs.filter(start_at__date=date)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='mine-driver')
    def mine_driver(self, request):
        """ログイン中ドライバー本人だけの予約"""
        if not request.user.groups.filter(name='DRIVER').exists():
            return Response(status=403)

        qs = self.filter_queryset(self.get_queryset())
        qs = qs.filter(driver__user=request.user)

        # ① 期間フィルタを追加
        date_from = request.query_params.get('from')
        date_to   = request.query_params.get('to')
        single    = request.query_params.get('date')

        if single:
            qs = qs.filter(start_at__date=single)
        else:
            if date_from:
                qs = qs.filter(start_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(start_at__date__lte=date_to)

        return Response(self.get_serializer(qs, many=True).data)


    @action(detail=False, methods=['get'], url_path='mine-cast')
    def mine_cast(self, request):
        if not request.user.groups.filter(name='CAST').exists():
            return Response(status=403)

        qs = self.filter_queryset(self.get_queryset())
        qs = qs.filter(casts__cast_profile__user=request.user)

        # ↓★ 期間フィルタを driver と同じ形で追加
        date_from = request.query_params.get('from')
        date_to   = request.query_params.get('to')
        single    = request.query_params.get('date')

        if single:
            qs = qs.filter(start_at__date=single)
        else:
            if date_from:
                qs = qs.filter(start_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(start_at__date__lte=date_to)

        return Response(self.get_serializer(qs, many=True).data)

class CastProfileViewSet(viewsets.ModelViewSet):
    queryset = CastProfile.objects.select_related('store', 'rank', 'performer')
    serializer_class = CastSerializer
    permission_classes = [IsStaff]          # STAFF だけ CRUD
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['store', 'rank', 'stage_name']
    
    # --- これだけ ---
    def get_queryset(self):
        qs = super().get_queryset()
        store_id = self.request.query_params.get("store")
        if store_id:
            qs = qs.filter(store_id=store_id)
        return qs