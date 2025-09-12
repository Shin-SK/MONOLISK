# billing/views.py
from datetime import date
from django.db import models, transaction
from django.db.models import Sum, F, Q, IntegerField, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import viewsets, status, mixins, generics, permissions, filters
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework.viewsets import ReadOnlyModelViewSet

from .permissions import RequireCap, CastHonshimeiForBill, CanOrderBillItem

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
# 共通: ユーザーがアクセスできる店舗IDの集合を得る
#   ※ superuser でも “全店舗” は返さない（所属/関係のある店舗のみ）
# ────────────────────────────────────────────────────────────────────
def user_store_ids(user):
    if not getattr(user, "is_authenticated", False):
        return set()

    ids = set()

    # 1) StoreMembership を一次情報に
    from accounts.models import StoreMembership
    ids.update(StoreMembership.objects.filter(user=user).values_list("store_id", flat=True))

    # 2) 既存の互換（必要なら残す）
    from .models import Staff, Cast
    ids.update(Cast.objects.filter(user=user).values_list("store_id", flat=True))
    for st in Staff.objects.filter(user=user).prefetch_related("stores"):
        ids.update(st.stores.values_list("id", flat=True))

    # 3) 旧フィールド互換
    sid = getattr(user, "store_id", None)
    if sid:
        ids.add(sid)

    return ids

class CacheListMixin:
	@method_decorator(cache_page(60 * 10))            # ← 10分(=600秒)
	@method_decorator(vary_on_headers('X-Store-Id'))  # ← 店舗ごとに別キャッシュ
	def list(self, request, *args, **kwargs):
		return super().list(request, *args, **kwargs)


# ────────────────────────────────────────────────────────────────────
# Store スコープ Mixin（あなたの StoreScopedModelViewSet を強化）
#   - require_store(): store_id を決定（指定があれば所属確認、無指定は単一所属なら自動）
#   - filter_queryset_by_store(): モデルに store_id があれば自店に絞る
#   - create/update 時に store を強制注入 or 不正を拒否
# ────────────────────────────────────────────────────────────────────
class StoreScopedModelViewSet(viewsets.ModelViewSet):
    """
    * GET   → 自店のみ（モデルに store/store_id がある場合）
    * POST  → store_id（ない/不一致なら自動上書き）
    * PATCH → store_id を自店に固定（他店への付け替え不可）
    """

    # --- store 決定（クエリ/body の store_id 優先 → 所属単一なら自動） ---
    def require_store(self, request):
        # ミドルウェアで決まっていることが前提
        s = getattr(request, "store", None)
        if not getattr(s, "id", None):
            raise ValidationError({"store_id": "X-Store-Id header is required."})
        sid = s.id

        # ★ ここで所属チェック（DRFは既に Token 認証済み）
        user = request.user
        if not (getattr(user, "is_superuser", False) or sid in user_store_ids(user)):
            raise PermissionDenied("この店舗へのアクセス権がありません。")

        return sid

    # --- QuerySet を自店に絞る（store_id を持つモデルのみ） ---
    def filter_queryset_by_store(self, qs, store_id):
        model = qs.model
        # 典型: store(FK) か store_id(列) を持つモデル
        concrete = {f.attname for f in model._meta.concrete_fields}
        if "store_id" in concrete:
            return qs.filter(store_id=store_id)
        if "store_id" in [f.name for f in model._meta.get_fields()]:
            return qs.filter(store_id=store_id)
        if "store" in [f.name for f in model._meta.get_fields()]:
            return qs.filter(store_id=store_id)
        # store を持たない（顧客など） → そのまま
        return qs

    # --- GET: 自店フィルタ ---
    def get_queryset(self):
        qs = super().get_queryset()
        try:
            sid = self.require_store(self.request)
        except Exception:
            # 一部の完全グローバル資源（本当にロック不要なもの）があればここでそのまま返す
            # ただしセキュリティ上、基本は require_store() で縛ること推奨
            return qs
        return self.filter_queryset_by_store(qs, sid)

    # --- POST: store を注入 or 不正修正 ---
    def perform_create(self, serializer):
        sid = self.require_store(self.request)
        field_names = [f.name for f in serializer.Meta.model._meta.get_fields()]
        # body に他店の store が来ても上書き
        if "store" in field_names:
            serializer.save(store_id=sid)
        elif "store_id" in field_names:
            serializer.save(store_id=sid)
        else:
            serializer.save()

    # --- PATCH/PUT: store の付け替え禁止（来ても自店に固定） ---
    def perform_update(self, serializer):
        sid = self.require_store(self.request)
        field_names = [f.name for f in serializer.Meta.model._meta.get_fields()]
        if "store" in field_names or "store_id" in field_names:
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
    def my(self, request):
        ids = user_store_ids(request.user)
        qs = Store.objects.filter(id__in=ids).order_by("id")
        return Response(StoreSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def me(self, request):
        sid = self.require_store(request)
        obj = get_object_or_404(Store, pk=sid)
        return Response(self.get_serializer(obj).data)

# ────────────────────────────────────────────────────────────────────
# 商品マスタ / 卓
# ────────────────────────────────────────────────────────────────────
class ItemMasterViewSet(CacheListMixin, StoreScopedModelViewSet):
    queryset = ItemMaster.objects.select_related("category")
    serializer_class = ItemMasterSerializer


class TableViewSet(CacheListMixin, StoreScopedModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    

# ────────────────────────────────────────────────────────────────────
# 伝票
# ────────────────────────────────────────────────────────────────────
class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer

    def _sid(self):
        return StoreScopedModelViewSet.require_store(self, self.request)
    
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
        
        # in/out 切替では main は変わらない（本指名トグルではない）
        new_main = prev_main

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
            prev_main, new_main,
            prev_in, new_in,
        )
        return Response({"stay_type": stay.stay_type}, status=status.HTTP_200_OK)


# ────────────────────────────────────────────────────────────────────
# 伝票明細
# ────────────────────────────────────────────────────────────────────
class BillItemViewSet(viewsets.ModelViewSet):
    serializer_class = BillItemSerializer
    permission_classes = [permissions.IsAuthenticated, CanOrderBillItem]

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        return (
            BillItem.objects
            .select_related("bill", "bill__table", "item_master")
            .filter(bill_id=self.kwargs["bill_pk"], bill__table__store_id=sid)
        )

    def perform_create(self, serializer):
        request = self.request
        sid = StoreScopedModelViewSet.require_store(self, request)
        bill = get_object_or_404(Bill.objects.select_related("table__store"), pk=self.kwargs["bill_pk"])
        if bill.table.store_id != sid:
            raise PermissionDenied("他店舗の伝票です。")

        # ★ オブジェクト（bill）に対する権限判定
        self.check_object_permissions(request, bill)

        # 商品の所属チェックは従来通り
        im = serializer.validated_data.get("item_master")
        if im and getattr(im, "store_id", None) not in (None, bill.table.store_id):
            raise ValidationError({"item_master": "他店舗の商品は使用できません。"})

        # served_by_cast の自動補完（従来通り）
        extra = {}
        user = request.user
        cast = Cast.objects.filter(user=user).first()
        is_staff_user = Staff.objects.filter(user=user).exists()
        if cast and not is_staff_user and not serializer.validated_data.get("served_by_cast"):
            extra["served_by_cast"] = cast

        serializer.save(bill=bill, **extra)



# ────────────────────────────────────────────────────────────────────
#（旧：サービス集計API）※当面は from/to のみ対応
# ────────────────────────────────────────────────────────────────────
class CastSalesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        today = date.today().isoformat()
        date_from = request.query_params.get("from", today)
        date_to   = request.query_params.get("to",   today)
        sid = StoreScopedModelViewSet.require_store(self, request)
        data = get_cast_sales(date_from, date_to, store_id=sid)
        return Response(data)


# ────────────────────────────────────────────────────────────────────
# キャスト / 明細・配分
# ────────────────────────────────────────────────────────────────────
class CastViewSet(CacheListMixin, StoreScopedModelViewSet):
    queryset = Cast.objects.select_related("store").prefetch_related("category_rates")
    serializer_class = CastSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["user__is_active", "stage_name", "user__username"]


class CastPayoutListView(generics.ListAPIView):
    serializer_class = CastPayoutDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class  = CastPayoutFilter

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
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
    filterset_class  = CastItemFilter

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        cid = self.request.query_params.get("cast")
        f   = self.request.query_params.get("from")
        t   = self.request.query_params.get("to")

        qs = (
            BillItem.objects
            .select_related("bill", "bill__table", "item_master__category")
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
        sid = self.require_store(self.request)
        if not serializer.validated_data.get("store"):
            serializer.save(store_id=sid)
        else:
            serializer.save()


class CastDailySummaryViewSet(StoreScopedModelViewSet):
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
    serializer_class = CastSalesSummarySerializer
    pagination_class = None
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        f = self.request.query_params.get("from")
        t = self.request.query_params.get("to")
        if not (f and t):
            today = timezone.localdate()
            f = today.replace(day=1)
            t = today
        date_q = Q(daily_summaries__work_date__range=(f, t))
        return (
            Cast.objects.filter(store_id=sid)
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
    pagination_class = None
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        df = self.request.query_params.get("from")
        dt = self.request.query_params.get("to")
        if not (df and dt):
            today = timezone.localdate()
            df = today.replace(day=1)
            dt = today
        revenue_expr = (
            F("daily_summaries__sales_free") + F("daily_summaries__sales_in") +
            F("daily_summaries__sales_nom")  + F("daily_summaries__sales_champ")
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
        sid = StoreScopedModelViewSet.require_store(self, self.request)
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
    serializer_class = BillCastStayMiniSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        bill_id = self.kwargs["bill_pk"]
        return (
            BillCastStay.objects
            .select_related("bill", "bill__table")
            .filter(bill_id=bill_id, bill__table__store_id=sid)
        )

    def perform_create(self, serializer):
        sid  = StoreScopedModelViewSet.require_store(self, self.request)
        bill = get_object_or_404(Bill.objects.select_related("table__store"), pk=self.kwargs["bill_pk"])
        if bill.table.store_id != sid:
            raise PermissionDenied("他店舗の伝票です。")
        cast = serializer.validated_data.get("cast")
        if cast and cast.store_id != bill.table.store_id:
            raise ValidationError({"cast": "他店舗のキャストは追加できません。"})

        stay = serializer.save(bill=bill, entered_at=timezone.now())

        if stay.stay_type == "nom" and not stay.is_honshimei:
            stay.is_honshimei = True
            stay.save(update_fields=["is_honshimei"])

    def perform_update(self, serializer):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        inst = serializer.instance
        if inst.bill.table.store_id != sid:
            raise PermissionDenied("他店舗の伝票です。")

        stay = serializer.save()
        if stay.stay_type == "nom" and not stay.is_honshimei:
            stay.is_honshimei = True
            stay.save(update_fields=["is_honshimei"])


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

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        qs = super().get_queryset().filter(store_id=sid)

        # 一般（キャスト等）は公開済のみ
        if not (self.request.user and self.request.user.is_staff):
            now = timezone.now()
            qs = qs.filter(is_published=True).filter(Q(publish_at__isnull=True) | Q(publish_at__lte=now))

        # 管理側の追加フィルタ
        status_ = self.request.query_params.get("status")
        if status_ and self.request.user and self.request.user.is_staff:
            now = timezone.now()
            if status_ == "draft":
                qs = qs.filter(is_published=False)
            elif status_ == "scheduled":
                qs = qs.filter(is_published=True, publish_at__gt=now)
            elif status_ == "published":
                qs = qs.filter(is_published=True).filter(Q(publish_at__isnull=True) | Q(publish_at__lte=now))

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
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        serializer.save(store_id=sid)

    def perform_update(self, serializer):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        serializer.save(store_id=sid)


