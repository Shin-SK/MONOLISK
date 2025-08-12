# billing/views.py
from datetime import date
from django.db import models, transaction
from django.db.models import Sum, F, Q, IntegerField, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import viewsets, status, mixins, generics, permissions, filters
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Store, Table, Bill, ItemMaster, BillItem, BillCastStay,
    Cast, CastPayout, ItemCategory, CastShift, CastDailySummary,
    Staff, StaffShift, Customer, CustomerLog, StoreNotice,
)
from .serializers import (
    StoreSerializer, TableSerializer, BillSerializer,
    ItemMasterSerializer, BillItemSerializer,
    CastSerializer, CastShiftSerializer, CastDailySummarySerializer,
    CastPayoutDetailSerializer, CastItemDetailSerializer,
    CastRankingSerializer, CastSalesSummarySerializer,
    StaffSerializer, StaffShiftSerializer,
    BillCastStayMiniSerializer, CustomerSerializer, CustomerLogSerializer,
    StoreNoticeSerializer, ItemCategorySerializer,
)
from .filters import CastPayoutFilter, CastItemFilter
from .services import get_cast_sales, sync_nomination_fees
from billing.utils.customer_log import log_customer_change


# ────────────────────────────────────────────────────────────────────
# 共通: 自店スコープ（Store-Locked 原則）
# ────────────────────────────────────────────────────────────────────
class StoreScopedModelViewSet(viewsets.ModelViewSet):
    """
    * GET   → 自店フィルタ
    * POST  → store を自動注入
    * PATCH → store を強制固定
    """
    def _store(self, request):
        s = getattr(request, "store", None)
        if getattr(s, "id", None):
            return s.id
        uid = getattr(getattr(request, "user", None), "store_id", None)
        if uid:
            return uid
        raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})

    def get_queryset(self):
        qs = super().get_queryset()
        sid = self._store(self.request)
        if qs.model is Store:
            return qs.filter(pk=sid)
        # concrete fields だけを見て store_id を判定
        if "store_id" in [f.attname for f in qs.model._meta.concrete_fields]:
            return qs.filter(store_id=sid)
        return qs

    def perform_create(self, serializer):
        sid = self._store(self.request)
        field_names = [f.name for f in serializer.Meta.model._meta.get_fields()]
        if "store" in field_names:
            serializer.save(store_id=sid)
        else:
            serializer.save()

    def perform_update(self, serializer):
        sid = self._store(self.request)
        field_names = [f.name for f in serializer.Meta.model._meta.get_fields()]
        if "store" in field_names:
            serializer.save(store_id=sid)
        else:
            serializer.save()


# ────────────────────────────────────────────────────────────────────
# 店舗
# ────────────────────────────────────────────────────────────────────
class StoreViewSet(StoreScopedModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

    @action(detail=False, methods=["get"])
    def me(self, request):
        sid = self._store(request)
        obj = get_object_or_404(Store, pk=sid)
        return Response(self.get_serializer(obj).data)


# ────────────────────────────────────────────────────────────────────
# 商品マスタ / 卓
# ────────────────────────────────────────────────────────────────────
class ItemMasterViewSet(StoreScopedModelViewSet):
    queryset = ItemMaster.objects.select_related("category")
    serializer_class = ItemMasterSerializer


class TableViewSet(StoreScopedModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer


# ────────────────────────────────────────────────────────────────────
# 伝票
# ────────────────────────────────────────────────────────────────────
class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer

    def _sid(self):
        # StoreScopedModelViewSet のロジックを借用
        s = getattr(self.request, "store", None)
        if getattr(s, "id", None):
            return s.id
        uid = getattr(getattr(self.request, "user", None), "store_id", None)
        if uid:
            return uid
        raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})

    def get_queryset(self):
        sid = self._sid()
        return (
            Bill.objects
            .select_related("table__store")
            .prefetch_related("items", "stays", "nominated_casts")
            .filter(table__store_id=sid)
            .order_by("-opened_at")
        )

    def perform_create(self, serializer):
        sid = self._sid()
        table = serializer.validated_data.get("table")
        if not table or table.store_id != sid:
            raise ValidationError({"table": "他店舗の卓は指定できません。"})
        serializer.save()

    def perform_update(self, serializer):
        sid = self._sid()
        table = serializer.validated_data.get("table", getattr(serializer.instance, "table", None))
        if table and table.store_id != sid:
            raise ValidationError({"table": "他店舗の卓は指定できません。"})
        serializer.save()

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        bill = self.get_object()
        with transaction.atomic():
            bill.close(settled_total=request.data.get("settled_total"))
        return Response(self.get_serializer(bill).data)

    @action(detail=True, methods=["post"], url_path="toggle-inhouse")
    def toggle_inhouse(self, request, pk=None):
        """
        cast_id と inhouse(bool) を受け取り、
        BillCastStay.stay_type を 'in' / 'free' に切替。
        さらに houseNom-fee 行を差分同期。
        """
        bill = self.get_object()
        cid = int(request.data.get("cast_id"))
        want_in = bool(request.data.get("inhouse"))

        # ① 変更前の inhouse & main をキャッシュ
        prev_in = set(
            bill.stays.filter(stay_type="in", left_at__isnull=True)
            .values_list("cast_id", flat=True)
        )
        prev_main = set(bill.nominated_casts.values_list("id", flat=True))

        stay, _ = BillCastStay.objects.get_or_create(
            bill=bill, cast_id=cid,
            defaults=dict(entered_at=timezone.now(), stay_type="free"),
        )
        stay.stay_type = "in" if want_in else "free"
        stay.left_at = None
        stay.save(update_fields=["stay_type", "left_at"])

        # ② 変更後の inhouse
        new_in = set(
            bill.stays.filter(stay_type="in", left_at__isnull=True)
            .values_list("cast_id", flat=True)
        )

        # ③ 差分にもとづき fee 行を同期
        sync_nomination_fees(
            bill,
            prev_main, prev_main,   # 本指名は不変
            prev_in, new_in,
        )
        return Response({"stay_type": stay.stay_type}, status=status.HTTP_200_OK)


# ────────────────────────────────────────────────────────────────────
# 伝票明細
# ────────────────────────────────────────────────────────────────────
class BillItemViewSet(viewsets.ModelViewSet):
    serializer_class = BillItemSerializer

    def get_queryset(self):
        sid = getattr(getattr(self.request, "user", None), "store_id", None) or getattr(getattr(self.request, "store", None), "id", None)
        if not sid:
            raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})
        return (
            BillItem.objects
            .select_related("bill", "bill__table", "item_master")
            .filter(bill_id=self.kwargs["bill_pk"], bill__table__store_id=sid)
        )

    def perform_create(self, serializer):
        bill = get_object_or_404(Bill.objects.select_related("table__store"), pk=self.kwargs["bill_pk"])
        im = serializer.validated_data.get("item_master")
        if im and getattr(im, "store_id", None) not in (None, bill.table.store_id):
            raise ValidationError({"item_master": "他店舗の商品は使用できません。"})
        serializer.save(bill=bill)


# ────────────────────────────────────────────────────────────────────
#（旧：サービス集計API）※当面は from/to のみ対応
# ────────────────────────────────────────────────────────────────────
class CastSalesView(APIView):
    def get(self, request):
        today = date.today().isoformat()
        date_from = request.query_params.get("from", today)
        date_to   = request.query_params.get("to",   today)

        sid = getattr(getattr(request, "store", None), "id", None) or getattr(request.user, "store_id", None)
        if not sid:
            raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})

        data = get_cast_sales(date_from, date_to, store_id=sid)
        return Response(data)


# ────────────────────────────────────────────────────────────────────
# キャスト / 明細・配分
# ────────────────────────────────────────────────────────────────────
class CastViewSet(StoreScopedModelViewSet):
    queryset = (
        Cast.objects
        .select_related("store")
        .prefetch_related("category_rates")
    )
    serializer_class = CastSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["user__is_active", "stage_name", "user__username"]


class CastPayoutListView(generics.ListAPIView):
    serializer_class = CastPayoutDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CastPayoutFilter

    def get_queryset(self):
        sid = getattr(getattr(self.request, "store", None), "id", None) or getattr(self.request.user, "store_id", None)
        if not sid:
            raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})

        qs = (
            CastPayout.objects
            .select_related("cast", "bill", "bill__table", "bill_item", "bill_item__item_master")
            .filter(bill__isnull=False, bill__table__store_id=sid)
        )

        if (cid := self.request.query_params.get("cast")):
            qs = qs.filter(cast_id=cid)

        f = self.request.query_params.get("from")
        t = self.request.query_params.get("to")
        if f and t:
            qs = qs.filter(bill__closed_at__date__range=(f, t))

        return qs.order_by("-bill__closed_at")


class CastItemDetailView(generics.ListAPIView):
    serializer_class = CastItemDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CastItemFilter

    def get_queryset(self):
        sid = getattr(getattr(self.request, "store", None), "id", None) or getattr(self.request.user, "store_id", None)
        if not sid:
            raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})

        cid = self.request.query_params.get("cast")
        f   = self.request.query_params.get("from")
        t   = self.request.query_params.get("to")

        qs = (
            BillItem.objects
            .select_related("bill", "bill__table")
            .filter(bill__closed_at__isnull=False, bill__table__store_id=sid)
        )

        if cid:
            qs = qs.filter(
                Q(served_by_cast_id=cid) |
                Q(is_nomination=True) & (
                    Q(bill__main_cast_id=cid) |
                    Q(bill__nominated_casts__id=cid)
                )
            )

        if f and t:
            qs = qs.filter(bill__closed_at__date__range=(f, t))

        return qs.distinct().order_by("-bill__closed_at")


class ItemCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /item-categories/      一覧
    GET /item-categories/<pk>/ 単件
    （作成・更新・削除は admin から行う想定）
    """
    queryset = ItemCategory.objects.all()
    serializer_class = ItemCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


# ────────────────────────────────────────────────────────────────────
# シフト / 日次サマリ / 売上サマリ / ランキング
# ────────────────────────────────────────────────────────────────────
class CastShiftViewSet(StoreScopedModelViewSet):
    queryset = CastShift.objects.select_related("store", "cast")
    serializer_class = CastShiftSerializer
    filterset_fields = ["cast", "clock_in", "clock_out"]

    def perform_create(self, serializer):
        sid = self._store(self.request)
        if not serializer.validated_data.get("store"):
            serializer.save(store_id=sid)
        else:
            serializer.save()


class CastDailySummaryViewSet(StoreScopedModelViewSet):
    """
    GET /billing/cast-daily-summaries/?from=YYYY-MM-DD&to=YYYY-MM-DD&cast=ID
    """
    serializer_class = CastDailySummarySerializer
    queryset = CastDailySummary.objects.select_related("cast", "store")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["cast", "work_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        f = self.request.query_params.get("from")
        t = self.request.query_params.get("to")
        if f and t:
            qs = qs.filter(work_date__range=(f, t))
        return qs.order_by("cast__stage_name", "work_date")


class CastSalesSummaryView(ListAPIView):
    """
    GET /api/billing/cast-sales-summary/?from=YYYY-MM-DD&to=YYYY-MM-DD
    └ 期間未指定なら当月
    """
    serializer_class = CastSalesSummarySerializer
    pagination_class = None

    def get_queryset(self):
        sid = getattr(getattr(self.request, "store", None), "id", None) or getattr(self.request.user, "store_id", None)
        if not sid:
            raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})

        f = self.request.query_params.get("from")
        t = self.request.query_params.get("to")
        if not (f and t):
            today = timezone.localdate()
            f = today.replace(day=1)
            t = today

        date_q = Q(daily_summaries__work_date__range=(f, t))

        return (
            Cast.objects
            .filter(store_id=sid)
            .annotate(
                sales_champ=Coalesce(Sum("daily_summaries__sales_champ", filter=date_q), Value(0)),
                sales_nom  =Coalesce(Sum("daily_summaries__sales_nom",   filter=date_q), Value(0)),
                sales_in   =Coalesce(Sum("daily_summaries__sales_in",    filter=date_q), Value(0)),
                sales_free =Coalesce(Sum("daily_summaries__sales_free",  filter=date_q), Value(0)),
                payroll    =Coalesce(Sum("daily_summaries__payroll",     filter=date_q), Value(0)),
                total=F("sales_champ") + F("sales_nom") + F("sales_in") + F("sales_free"),
            )
            .order_by("stage_name")
        )


class CastRankingView(ListAPIView):
    serializer_class = CastRankingSerializer
    pagination_class = None  # 上位10名だけ

    def get_queryset(self):
        sid = getattr(getattr(self.request, "store", None), "id", None) or getattr(self.request.user, "store_id", None)
        if not sid:
            raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})

        df = self.request.query_params.get("from")
        dt = self.request.query_params.get("to")
        if not (df and dt):
            today = timezone.localdate()
            df = today.replace(day=1)
            dt = today

        revenue_expr = (
            F("daily_summaries__sales_free") +
            F("daily_summaries__sales_in") +
            F("daily_summaries__sales_nom") +
            F("daily_summaries__sales_champ")
        )

        return (
            Cast.objects
            .filter(store_id=sid, daily_summaries__work_date__range=(df, dt))
            .annotate(revenue=Sum(revenue_expr, output_field=IntegerField()))
            .select_related("store")
            .order_by("-revenue")[:10]
        )


# ────────────────────────────────────────────────────────────────────
# スタッフ / スタッフシフト（M2M に注意）
# ────────────────────────────────────────────────────────────────────
class StaffViewSet(viewsets.ModelViewSet):
    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["user__username", "stores"]

    def get_queryset(self):
        sid = getattr(getattr(self.request, "store", None), "id", None) or getattr(self.request.user, "store_id", None)
        if not sid:
            raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})
        return (
            Staff.objects
            .filter(stores__id=sid)
            .prefetch_related("stores", "user")
            .distinct()
        )


class StaffShiftViewSet(StoreScopedModelViewSet):
    queryset = StaffShift.objects.select_related("store", "staff")
    serializer_class = StaffShiftSerializer
    filterset_fields = ["staff", "clock_in", "clock_out"]


# ────────────────────────────────────────────────────────────────────
# 在席行（stays）
# ────────────────────────────────────────────────────────────────────
class BillStayViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    POST   /billing/bills/<bill_id>/stays/
    PATCH  /billing/bills/<bill_id>/stays/<id>/
    DELETE /billing/bills/<bill_id>/stays/<id>/
    """
    serializer_class = BillCastStayMiniSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        sid = getattr(getattr(self.request, "store", None), "id", None) or getattr(self.request.user, "store_id", None)
        if not sid:
            raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})
        bill_id = self.kwargs["bill_pk"]
        return (
            BillCastStay.objects
            .select_related("bill", "bill__table")
            .filter(bill_id=bill_id, bill__table__store_id=sid)
        )

    def perform_create(self, serializer):
        bill = get_object_or_404(Bill.objects.select_related("table__store"),
                                 pk=self.kwargs["bill_pk"])
        cast = serializer.validated_data.get("cast")
        if cast and cast.store_id != bill.table.store_id:
            raise ValidationError({"cast": "他店舗のキャストは追加できません。"})
        serializer.save(bill=bill, entered_at=timezone.now())

    def partial_update(self, request, *args, **kwargs):
        # PATCH で “退席させる” ショートハンド
        if request.data.get("left_now"):
            instance = self.get_object()
            instance.left_at = timezone.now()
            instance.save(update_fields=["left_at"])
            ser = self.get_serializer(instance)
            return Response(ser.data, status=status.HTTP_200_OK)
        return super().partial_update(request, *args, **kwargs)


# ────────────────────────────────────────────────────────────────────
# 顧客
# ────────────────────────────────────────────────────────────────────
class CustomerViewSet(viewsets.ModelViewSet):
    """
    /api/customers/?q= 検索（氏名・あだ名・電話）
    ※ 現状グローバル。将来は store FK 追加を検討。
    """
    queryset = Customer.objects.all().order_by("-updated_at")
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(alias__icontains=q) |
                Q(phone__icontains=q)
            )
        return qs

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        logs = CustomerLog.objects.filter(customer_id=pk).order_by("-at")
        page = self.paginate_queryset(logs)
        if page is not None:
            ser = CustomerLogSerializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = CustomerLogSerializer(logs, many=True)
        return Response(ser.data)

    def perform_create(self, serializer):
        instance = serializer.save()
        log_customer_change(self.request.user, instance, "create", {}, serializer.data)

    def perform_update(self, serializer):
        before = CustomerSerializer(instance=serializer.instance).data
        instance = serializer.save()
        after = CustomerSerializer(instance=instance).data
        log_customer_change(self.request.user, instance, "update", before, after)


# ────────────────────────────────────────────────────────────────────
# 店舗お知らせ（StoreNotice）— 自店ロック
# ────────────────────────────────────────────────────────────────────
class NewsPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class IsStaffOrReadOnly(permissions.BasePermission):
    """スタッフはCRUD可、その他（キャスト等）は読み取りのみ。"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class StoreNoticeViewSet(viewsets.ModelViewSet):
    queryset = StoreNotice.objects.all()
    serializer_class = StoreNoticeSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = NewsPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "body"]
    ordering_fields = ["publish_at", "created_at", "pinned"]
    ordering = ["-pinned", "-publish_at", "-created_at"]

    def _sid(self, request):
        s = getattr(request, "store", None)
        if getattr(s, "id", None):
            return s.id
        uid = getattr(getattr(request, "user", None), "store_id", None)
        if uid:
            return uid
        raise ValidationError({"store": "ユーザーに店舗が紐付いていません。"})

    def get_queryset(self):
        qs = super().get_queryset()
        sid = self._sid(self.request)
        qs = qs.filter(store_id=sid)

        # 一般（キャスト等）は “見えるものだけ”
        if not (self.request.user and self.request.user.is_staff):
            now = timezone.now()
            qs = qs.filter(is_published=True).filter(Q(publish_at__isnull=True) | Q(publish_at__lte=now))

        # 追加フィルタ（管理側用）
        status_ = self.request.query_params.get("status")
        if status_ and self.request.user and self.request.user.is_staff:
            now = timezone.now()
            if status_ == "draft":
                qs = qs.filter(is_published=False)
            elif status_ == "scheduled":
                qs = qs.filter(is_published=True, publish_at__gt=now)
            elif status_ == "published":
                qs = qs.filter(is_published=True).filter(Q(publish_at__isnull=True) | Q(publish_at__lte=now))

        # is_published / pinned
        ip = self.request.query_params.get("is_published")
        if ip is not None:
            if ip in ("1", "true", "True"):
                qs = qs.filter(is_published=True)
            elif ip in ("0", "false", "False"):
                qs = qs.filter(is_published=False)

        pinned = self.request.query_params.get("pinned")
        if pinned in ("1", "true", "True"):
            qs = qs.filter(pinned=True)
        elif pinned in ("0", "false", "False"):
            qs = qs.filter(pinned=False)

        return qs

    def perform_create(self, serializer):
        sid = self._sid(self.request)
        serializer.save(store_id=sid)

    def perform_update(self, serializer):
        sid = self._sid(self.request)
        serializer.save(store_id=sid)
