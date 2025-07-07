#veiws.py
from rest_framework import viewsets, permissions ,filters, status, mixins
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .filters import CustomerFilter
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef, Q, Sum, Subquery, IntegerField, Value, Case, When, F, DateField, ExpressionWrapper
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import date, timedelta
from calendar import monthrange
from django.db.models.functions import TruncDate, TruncMonth
from core.utils.pl import get_daily_pl, get_monthly_pl, get_yearly_pl
from django.conf import settings
from datetime import datetime
from rest_framework.pagination import LimitOffsetPagination

from .models import (
    Store, Rank, Course, RankCourse, Option, GroupOptionPrice,
    CastProfile, CastCoursePrice, CastOption, Driver, Customer,
    Reservation, ReservationCast, CustomerAddress, ShiftPlan, ShiftAttendance, ReservationDriver, DriverShift, ExpenseCategory, ExpenseEntry, CastRate, DriverRate
)
from .serializers import (
    StoreSerializer, RankSerializer, CourseSerializer, RankCourseSerializer,
    OptionSerializer, GroupOptionPriceSerializer,
    CastSerializer, CastCoursePriceSerializer, CastOptionSerializer,
    DriverSerializer, CustomerSerializer, ReservationSerializer, DriverListSerializer,
    CustomerReservationSerializer,CustomerAddressSerializer, ShiftPlanSerializer, ShiftAttendanceSerializer, ReservationDriverSerializer ,DriverShiftSerializer,
    ExpenseEntrySerializer, ExpenseCategorySerializer, DailyPLSerializer,
    DriverRateSerializer, CastRateSerializer, YearlyMonthSerializer
)
from.filters import (
    ReservationFilter,CastProfileFilter, CustomerFilter, ShiftPlanFilter, ReservationDriverFilter
)



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

# ---------- ドライバー ----------
class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.select_related('user','store')
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]
    # -- 出勤 -------------------------------------------------
    @action(detail=True, methods=['post'])
    def clock_in(self, request, pk=None):
        driver = self.get_object()
        today  = timezone.localdate()

        shift, created = DriverShift.objects.get_or_create(
            driver=driver, date=today,
            defaults={
                'float_start': request.data.get('float_start', 0),
                'clock_in_at': timezone.now(),
            }
        )
        ser = DriverShiftSerializer(shift)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    # -- 勤怠一覧（1ドライバー分） ----------------------------
    @action(detail=True, methods=['get'])
    def shifts(self, request, pk=None):
        driver = self.get_object()
        qs = driver.shifts.all()
        if date := request.query_params.get('date'):
            qs = qs.filter(date=date)
        return Response(DriverShiftSerializer(qs, many=True).data)



class DriverShiftViewSet(
        mixins.ListModelMixin,          # ★ 追加
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet):

    """
    /api/driver-shifts/<shift_id>/
        └─ PATCH clock_out/ … 退勤
    """
    queryset = DriverShift.objects.select_related('driver__user')
    serializer_class = DriverShiftSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends   = [DjangoFilterBackend]
    filterset_fields  = ['date', 'driver__store', 'driver']

    def get_queryset(self):
        qs = super().get_queryset()

        # STAFF 絞り込みはそのまま
        if not (self.request.user.is_superuser or
                self.request.user.groups.filter(name='STAFF').exists()):
            qs = qs.filter(driver__user=self.request.user)

        # --- 集金額サブクエリ ---

        rd_sub = (
            ReservationDriver.objects
            .filter(
                driver_id=OuterRef("driver_id"),
                reservation__start_at__date=OuterRef("date"),
                role=ReservationDriver.Role.DROP_OFF,
            )
            .annotate(          # ★ collected_amount 優先／無ければ received_amount
                effective_amount=Case(
                    When(collected_amount__isnull=True,
                        then=F("reservation__received_amount")),
                    default=F("collected_amount"),
                    output_field=IntegerField(),
                )
            )
            .values("driver_id")
            .annotate(s=Sum("effective_amount"))
            .values("s")[:1]
        )

        # ★ 別名で注入
        qs = qs.annotate(
            total_received_calc=Coalesce(Subquery(rd_sub, output_field=IntegerField()), Value(0))
        )

        return qs.order_by('driver_id')

    @action(detail=True, methods=['post'])
    def clock_in(self, request, pk=None):
        """
        ● STAFF  … /api/driver-shifts/<driver_id>/clock_in/
        ● 本人   … 同上（permission で制御）
        既に当日のシフトがあれば clock_in_at / float_start を上書き保存できる。
        Body:
            float_start : int     釣り銭（省略可）
            at          : str     "YYYY-MM-DDTHH:MM:SS"（省略可 → now）
        """
        driver = get_object_or_404(Driver, pk=pk)

        # ── 権限チェック ───────────────────────────────────
        if driver.user != request.user and not (
            request.user.is_superuser or
            request.user.groups.filter(name="STAFF").exists()
        ):
            return Response({"detail": "権限がありません"}, status=403)

        # ── 入力値パース ──────────────────────────────────
        at_raw = request.data.get("at")         # ISO8601 文字列 or None
        try:
            clock_in_at = (
                timezone.make_aware(datetime.fromisoformat(at_raw))
                if at_raw else timezone.now()
            )
        except (TypeError, ValueError):
            return Response({"at": "日時フォーマットが不正です"}, status=400)

        float_start = request.data.get("float_start", None)

        # ── シフト取得／生成 ───────────────────────────────
        shift, created = DriverShift.objects.get_or_create(
            driver=driver,
            date=clock_in_at.date(),            # “その日” のシフト
            defaults={
                "float_start": float_start or 0,
                "clock_in_at": clock_in_at,
            },
        )

        # ── 既存シフトなら値を上書き保存 ───────────────────
        if not created:
            changed_fields = []
            if at_raw:                          # 時刻を変更
                shift.clock_in_at = clock_in_at
                changed_fields.append("clock_in_at")
            if float_start is not None:         # 釣銭を変更
                shift.float_start = float_start
                changed_fields.append("float_start")
            if changed_fields:
                shift.save(update_fields=changed_fields)

        status_code = 201 if created else 200
        return Response(DriverShiftSerializer(shift).data, status=status_code)


    @action(detail=True, methods=['patch'])
    def clock_out(self, request, pk=None):
        shift = self.get_object()
        serializer = self.get_serializer(
            shift, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(clock_out_at=timezone.now())

        return Response(self.get_serializer(shift).data)



class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]
    filter_backends = [
        DjangoFilterBackend,
    ]
    search_fields   = ['phone', 'name']   # ← ② 追加
    filterset_class    = CustomerFilter

    @action(detail=True, methods=["get"])
    def latest_reservation(self, request, pk=None):
        """顧客の直近 1 件"""
        r = (
            Reservation.objects
            .filter(customer_id=pk)
            .order_by("-start_at")
            .select_related("store")
            .prefetch_related("casts__cast_profile")
            .first()
        )
        if not r:
            return Response(None)
        ser = CustomerReservationSerializer(r)
        return Response(ser.data)

    @action(detail=True, methods=["get"])
    def reservations(self, request, pk=None):
        """
        顧客の予約一覧（?limit=20 & ?offset=40 も使える）
        """
        qs = (
            Reservation.objects
            .filter(customer_id=pk)
            .order_by("-start_at")
            .select_related("store")
            .prefetch_related("casts__cast_profile")
        )
        # pagination は DRF のデフォルトをそのまま
        page = self.paginate_queryset(qs)
        ser  = CustomerReservationSerializer(page, many=True)
        return self.get_paginated_response(ser.data)


# ---------- 予約 ----------


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = (
        Reservation.objects
        .select_related("store", "driver", "customer")
        .prefetch_related(
            "casts__cast_profile",
            "charges",
            "drivers__driver__user",  # ★ 追加
        )
    )
    serializer_class    = ReservationSerializer
    permission_classes  = [AllowAny]
    pagination_class    = LimitOffsetPagination      # ← 必要なら外して OK

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class   = ReservationFilter 
    # filterset_fields = ['customer']	
    ordering_fields = ["start_at", "id"]      # 並び替え許可フィールド
    ordering = ["-start_at"]                  # ← デフォルトを新しい順に

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
        qs = qs.filter(
            Q(drivers__driver__user=request.user) |   # ← PU / DO 中間テーブル
            Q(driver__user=request.user)              # ← 旧 single FK (残していても OK)
        ).distinct()

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


    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """
        payload: { "ids": [1, 2, 3] }
        """
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {"detail": "ids を配列で送ってください"},
                status=status.HTTP_400_BAD_REQUEST
            )
        deleted, _ = Reservation.objects.filter(id__in=ids).delete()
        return Response({"deleted": deleted}, status=status.HTTP_204_NO_CONTENT)


class CastProfileViewSet(viewsets.ModelViewSet):
    queryset = CastProfile.objects.select_related("store", "rank", "performer")
    serializer_class = CastSerializer
    permission_classes = [IsStaff]
    filter_backends   = [DjangoFilterBackend]
    filterset_class   = CastProfileFilter
    pagination_class  = None
    # --- これだけ ---
    def get_queryset(self):
        qs = super().get_queryset()
        store_id = self.request.query_params.get("store")
        if store_id:
            qs = qs.filter(store_id=store_id)
        return qs



class CustomerAddressViewSet(viewsets.ModelViewSet):
	serializer_class = CustomerAddressSerializer
	permission_classes = [AllowAny]

	def get_queryset(self):
		return CustomerAddress.objects.filter(customer_id=self.kwargs['customer_pk'])

	def perform_create(self, serializer):			# ★ 追加
		customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
		serializer.save(customer=customer)




class ShiftPlanViewSet(viewsets.ModelViewSet):
    queryset = ShiftPlan.objects.all()          # ★ 追加
    serializer_class = ShiftPlanSerializer
    permission_classes = [IsStaff]
    filter_backends   = [DjangoFilterBackend]
    filterset_class   = ShiftPlanFilter

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("cast_profile__store")
            .annotate(
                is_checked_in = Exists(
                    ShiftAttendance.objects.filter(
                        shift_plan=OuterRef("pk"),
                        checked_out_at__isnull=True
                    )
                )
            )
        )
        # date 未指定なら今日
        if "date" not in self.request.query_params:
            qs = qs.filter(date=timezone.localdate())
        return qs

# core/views.py  ── 末尾あたりに追記
class ShiftAttendanceViewSet(viewsets.ModelViewSet):
    """打刻専用 ViewSet: /shift-attendances/<pk>/checkin|checkout/"""
    queryset           = ShiftAttendance.objects.all()
    serializer_class   = ShiftAttendanceSerializer
    http_method_names  = ["get", "post", "head", "options"]

    @action(detail=True, methods=["post"])
    def checkin(self, request, pk=None):
        sa = self.get_object()
        at = request.data.get("at") or timezone.now()
        sa.checked_in_at = at
        sa.save(update_fields=["checked_in_at"])
        return Response(self.get_serializer(sa).data)

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        sa = self.get_object()
        at = request.data.get("at") or timezone.now()
        sa.checked_out_at = at
        sa.save(update_fields=["checked_out_at"])
        return Response(self.get_serializer(sa).data)




class ReservationDriverViewSet(viewsets.ModelViewSet):
    """
    /api/reservation-drivers/
    - list: ?reservation=123 で予約ごとの PU/DO 一覧
    - create: ドライバーアサイン or 集金登録
    - partial_update (PATCH): 時刻や金額の確定
    """
    queryset         = ReservationDriver.objects.select_related(
        "driver__user", "reservation"
    )
    serializer_class = ReservationDriverSerializer
    filterset_class  = ReservationDriverFilter
    permission_classes = [permissions.IsAuthenticated]


class SalesSummary(APIView):
    permission_classes = [IsStaff]          # 適宜

    def get(self, request):
        # qs = Reservation.objects.filter(status=Reservation.Status.CLOSED) もし締めボタン的なの作るなら使う
        qs = Reservation.objects.all()

        store = request.GET.get('store')
        if store:
            qs = qs.filter(store_id=store)

        date_from = request.GET.get('from')
        date_to   = request.GET.get('to')

        if date_from:
            qs = qs.filter(start_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(start_at__date__lte=date_to)

        total = qs.aggregate(total=Sum('received_amount'))['total'] or 0

        # 今日 & 今月
        today = timezone.localdate()
        today_total = qs.filter(start_at__date=today)       \
                        .aggregate(t=Sum('received_amount'))['t'] or 0
        month_total = qs.filter(start_at__month=today.month,
                                start_at__year=today.year)  \
                        .aggregate(t=Sum('received_amount'))['t'] or 0

        return Response({
            'total': total,
            'today_total': today_total,
            'month_total': month_total
        })




class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.filter(is_active=True)
    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated]  # 適宜

class ExpenseEntryViewSet(viewsets.ModelViewSet):
    """
    /api/expenses/?date=2025-07-03&store=<id>
    """
    queryset = ExpenseEntry.objects.select_related('category', 'store')
    serializer_class = ExpenseEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends   = [DjangoFilterBackend]
    filterset_fields  = ['date', 'store', 'category']


class CastRateViewSet(viewsets.ModelViewSet):          # ← 読み書き可
    """
    /api/cast-rates/
        GET  ?cast_profile=<id>         … 最新レート取得
        POST {cast_profile, commission_pct, hourly_rate?, effective_from?}
    """
    queryset = CastRate.objects.all()
    serializer_class = CastRateSerializer
    permission_classes = [IsStaff]      # STAFF 以上なら登録可
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cast_profile']

class DriverRateViewSet(viewsets.ModelViewSet):
    """
    /api/driver-rates/
        GET  ?driver=<id>
        POST {driver, hourly_rate, effective_from?}
    """
    queryset = DriverRate.objects.all()
    serializer_class = DriverRateSerializer
    permission_classes = [IsStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['driver']


class DailyPLView(APIView):
    """
    /api/pl/daily/?date=2025-07-03&store=<id|null>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
         target = request.GET.get("date") or date.today().isoformat()
         store  = request.GET.get("store")
         data   = get_daily_pl(date.fromisoformat(target),
                               int(store) if store else None)
         return Response(data)


class MonthlyPLView(APIView):
    """
    /api/pl/monthly/?month=2025-07&store=<id|null>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        month_str = request.GET.get("month") or date.today().strftime("%Y-%m")
        yyyy, mm  = map(int, month_str.split("-"))
        store     = request.GET.get("store")

        # util で日次+月次集計
        data = get_monthly_pl(yyyy, mm, int(store) if store else None)
        return Response(data)



class YearlyPLView(APIView):
    """
    /api/pl/yearly/?year=2025&store=<id|null>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year  = int(request.GET.get("year", timezone.localdate().year))
        store = request.GET.get("store")
        months = get_yearly_pl(year, int(store) if store else None)

        # Serializer で月ごとに整形
        data = YearlyMonthSerializer(months, many=True).data
        return Response({"year": year, "store": store, "months": data})




class DriverCashAlertView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        TH = getattr(settings, "CASH_ALERT_THRESHOLD", 200_000)

        # --- DO 集金額サブクエリ --------------------------
        do_sub = (
            ReservationDriver.objects
            .filter(
                driver_id=OuterRef("driver_id"),
                reservation__start_at__date=today,
                role=ReservationDriver.Role.DROP_OFF,
            )
            .annotate(
                effective=Case(
                    When(collected_amount__isnull=True,
                         then=F("reservation__received_amount")),
                    default=F("collected_amount"),
                    output_field=IntegerField(),
                )
            )
            .values("driver_id")
            .annotate(s=Sum("effective"))
            .values("s")[:1]
        )

        qs = (
            DriverShift.objects
            .filter(date=today)
            .annotate(
                today_received = Coalesce(Subquery(do_sub, output_field=IntegerField()), Value(0)),
                cash_on_hand   = ExpressionWrapper(
                    F("today_received")
                    - Coalesce(F("actual_deposit"), Value(0))
                    - Coalesce(F("used_float"),     Value(0))
                    - Coalesce(F("expenses"),       Value(0)),
                    output_field=IntegerField()
                )
            )
            .filter(cash_on_hand__gt=TH)
            .select_related("driver__user")
        )

        alerts = [
            {
                "driver_id"  : s.driver_id,
                "driver_name": s.driver.user.display_name or s.driver.user.username,
                "cash"       : s.cash_on_hand,
            }
            for s in qs
        ]
        return Response({"threshold": TH, "alerts": alerts})


