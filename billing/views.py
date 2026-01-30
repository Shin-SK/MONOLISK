# billing/views.py
from datetime import date
from datetime import timedelta
from collections import defaultdict
from django.db import models, transaction
from django.db.models import Sum, F, Q, IntegerField, Value, OuterRef, Subquery, Count, Max
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
import csv
from io import StringIO
from django.http import HttpResponse

from rest_framework import viewsets, status, mixins, generics, permissions, filters, serializers
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page, cache_control
from django.views.decorators.vary import vary_on_headers
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.filters import SearchFilter

from .permissions import RequireCap, CastHonshimeiForBill, CanOrderBillItem

from .models import (
    Store, Table, Bill, BillCustomer, ItemMaster, BillItem, BillCastStay,
    Cast, CastPayout, ItemCategory, CastShift, CastDailySummary,
    Staff, StaffShift, Customer, CustomerLog, CustomerTag,
    StoreNotice, StoreSeatSetting, DiscountRule, BillTag,
    PersonnelExpenseCategory, PersonnelExpense, PersonnelExpenseSettlementEvent, PayrollRun
)
from .serializers import (
    StoreSerializer, TableSerializer, BillSerializer,
    ItemMasterSerializer, BillItemSerializer,
    CastSerializer, CastShiftSerializer, CastDailySummarySerializer,
    CastPayoutDetailSerializer, CastItemDetailSerializer,
    CastRankingSerializer, CastSalesSummarySerializer,
    StaffSerializer, StaffShiftSerializer,
    BillCastStayMiniSerializer, CustomerSerializer, CustomerLogSerializer,
    StoreNoticeSerializer, ItemCategorySerializer, StoreSeatSettingSerializer, DiscountRuleSerializer,
    CastPayoutListSerializer, CustomerTagSerializer, BillTagSerializer,
    PersonnelExpenseCategorySerializer, PersonnelExpenseSerializer, PersonnelExpenseSettlementEventSerializer,
)
from .filters import CastPayoutFilter, CastItemFilter
from .services import get_cast_sales, sync_nomination_fees
from billing.utils.customer_log import log_customer_change

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import CastGoal
from .serializers import CastGoalSerializer

from datetime import date
from django.db.models import Sum, F, Q, Value, IntegerField
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Cast, CastShift, CastPayout
from .serializers import (
    CastMiniSerializer,
    CastPayoutDetailSerializer,
    CastPayrollSummaryRowSerializer,
    CastPayoutListSerializer,
)
from .exports.payroll_run_csv import PayrollRunExportCSVView




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


def _can_edit_cast_goals(user, cast):
    # Cast本人 or（必要なら）店舗の mgr/submgr を許可
    if getattr(user, 'is_superuser', False):
        return True
    if getattr(cast, 'user_id', None) and user.id == cast.user_id:
        return True
    staff = getattr(user, 'staff', None)
    if staff and getattr(staff, 'role', None) in ('mgr', 'submgr'):
        try:
            return staff.stores.filter(id=cast.store_id).exists()
        except Exception:
            return True
    return False



class CacheListMixin:
    @method_decorator(cache_page(60 * 10))
    @method_decorator(vary_on_headers('X-Store-Id', 'Authorization'))  # ← 追加
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class NoStoreListMixin:
    """
    認証付きAPIをCDN/ブラウザにキャッシュさせない（即時反映用）
    """
    @method_decorator(cache_control(
        private=True,
        no_store=True,
        no_cache=True,
        must_revalidate=True,
        max_age=0,
    ))
    @method_decorator(vary_on_headers('X-Store-Id', 'Authorization'))
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
        # ★ ここを厳格化：例外を握りつぶさず必ず store で絞る
        sid = self.require_store(self.request)
        qs = super().get_queryset()
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
class ItemMasterViewSet(NoStoreListMixin, StoreScopedModelViewSet):
    queryset = ItemMaster.objects.select_related("category")
    serializer_class = ItemMasterSerializer


class TableViewSet(NoStoreListMixin, StoreScopedModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    

# ────────────────────────────────────────────────────────────────────
# 伝票
# ────────────────────────────────────────────────────────────────────
class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    queryset = Bill.objects.all()
    # DjangoFilterBackend はもう使わないので外してもOK
    # filter_backends = [DjangoFilterBackend]

    def _sid(self):
        # StoreScopedModelViewSet.require_store をそのまま利用
        return StoreScopedModelViewSet.require_store(self, self.request)

    def get_queryset(self):
        sid = self._sid()

        qs = (
            Bill.objects
            .select_related("table__store")
            .prefetch_related("items", "stays", "nominated_casts")
            .filter(table__store_id=sid)
            .order_by("-opened_at")
        )

        # ▼ ここで「?cast=◯◯」を stays 経由で絞る（＝担当キャストのみ）
        cast_id = self.request.query_params.get("cast")
        if cast_id:
            qs = qs.filter(stays__cast_id=cast_id).distinct()

        return qs

    def perform_create(self, serializer):
        sid = self._sid()
        table = serializer.validated_data.get("table")
        if not table or table.store_id != sid:
            raise ValidationError({"table": "他店舗の卓は指定できません。"})
        bill = serializer.save()
        
        # pax が指定されていれば、BillCustomer を同期
        from .services.bill_customer_sync import ensure_bill_customers_for_pax
        ensure_bill_customers_for_pax(bill)

    def perform_update(self, serializer):
        sid = self._sid()
        table = serializer.validated_data.get("table", getattr(serializer.instance, "table", None))
        if table and table.store_id != sid:
            raise ValidationError({"table": "他店舗の卓は指定できません。"})

        # discount_ruleが更新された場合、再計算を実行
        bill = serializer.instance
        discount_rule_updated = 'discount_rule' in serializer.validated_data
        service_toggle_updated = 'apply_service_charge' in serializer.validated_data
        tax_toggle_updated = 'apply_tax' in serializer.validated_data
        pax_updated = 'pax' in serializer.validated_data
        old_discount_rule_id = bill.discount_rule_id if hasattr(bill, 'discount_rule_id') else None

        serializer.save()

        # pax が更新された場合、BillCustomer を同期
        if pax_updated:
            bill.refresh_from_db()
            from .services.bill_customer_sync import ensure_bill_customers_for_pax
            ensure_bill_customers_for_pax(bill)

        # discount_ruleが変更された場合、金額を再計算
        if discount_rule_updated or service_toggle_updated or tax_toggle_updated:
            from .models import _recalc_bill_after_items_change
            bill.refresh_from_db()
            _recalc_bill_after_items_change(bill)

    @action(detail=True, methods=["get"], url_path="nomination-summaries")
    def nomination_summaries(self, request, pk=None):
        """
        本指名顧客ごとの「滞在期間内の卓小計」を返す
        
        GET /api/billing/bills/{bill_id}/nomination-summaries/
        
        Returns:
        {
            "bill_id": ...,
            "results": [
                {
                    "customer_id": ...,
                    "customer_name": "...",
                    "period_start": "2026-01-26T20:30:00Z",
                    "period_end": "2026-01-26T21:30:00Z",
                    "period_status": "complete",
                    "subtotal": "40000.00",
                    "cast_ids": [1, 2],
                    "num_casts": 2,
                    "per_cast_share": "20000.00"
                },
                ...
            ]
        }
        """
        bill = self.get_object()
        
        # サービス関数を呼び出す
        from .services.nomination_summary import build_nomination_summaries
        now = request.query_params.get("now")
        if now:
            try:
                from django.utils.dateparse import parse_datetime
                now = parse_datetime(now)
            except:
                now = None
        
        summaries = build_nomination_summaries(bill, now=now)
        
        return Response({
            "bill_id": bill.id,
            "results": summaries
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="customers")
    def customers(self, request, pk=None):
        """
        この伝票の本指名顧客（BillCustomer）一覧を返す
        
        GET /api/billing/bills/{bill_id}/customers/
        
        Returns:
        {
            "results": [
                {
                    "id": 123,
                    "customer_id": 45,
                    "customer_name": "田中太郎",
                    "display_name": "田中太郎",
                    "arrived_at": "2026-01-26T20:30:00Z",
                    "left_at": null
                },
                ...
            ]
        }
        """
        bill = self.get_object()
        
        from .models import BillCustomer
        from .serializers_timeline import BillCustomerSerializer
        import logging
        logger = logging.getLogger(__name__)
        
        bill_customers = BillCustomer.objects.filter(bill=bill).select_related("customer").order_by('id')
        
        # デバッグログ：実際のクエリ結果を確認
        logger.info(f"[customers API] bill_id={bill.id}, queryset count={bill_customers.count()}")
        for bc in bill_customers:
            logger.info(f"  - BillCustomer id={bc.id}, customer_id={bc.customer_id}, arrived_at={bc.arrived_at}, left_at={bc.left_at}")
        
        serializer = BillCustomerSerializer(bill_customers, many=True)
        
        # デバッグログ：シリアライズ後の件数
        logger.info(f"[customers API] serialized data count={len(serializer.data)}")
        
        return Response({
            "results": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"], url_path="nominations")
    def nominations(self, request, pk=None):
        """
        この伝票の本指名設定（BillCustomerNomination）を管理
        
        GET  /api/billing/bills/{bill_id}/nominations/
        POST /api/billing/bills/{bill_id}/nominations/ body: { customer_id, cast_ids: [] }
        
        Returns (GET):
        {
            "results": [
                {
                    "id": 1,
                    "bill_id": 10,
                    "customer_id": 45,
                    "cast_id": 100,
                    ...
                },
                ...
            ]
        }
        """
        from .models import BillCustomerNomination
        from .serializers_timeline import BillCustomerNominationSerializer
        
        bill = self.get_object()
        
        if request.method == "GET":
            # 指定bill配下の全Nomination を返す
            nominations = BillCustomerNomination.objects.filter(bill=bill).select_related("customer", "cast")
            serializer = BillCustomerNominationSerializer(nominations, many=True)
            return Response({
                "results": serializer.data
            }, status=status.HTTP_200_OK)
        
        elif request.method == "POST":
            # 顧客 + キャスト群を POST
            customer_id = request.data.get("customer_id")
            cast_ids = request.data.get("cast_ids", [])
            
            if not customer_id:
                return Response(
                    {"error": "customer_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            now = timezone.now()

            existing_qs = BillCustomerNomination.objects.filter(
                bill=bill,
                customer_id=customer_id
            ).select_related("cast")

            existing_by_cast = {n.cast_id: n for n in existing_qs}
            requested_cast_ids = set(cast_ids)

            # 既存のうち外れたものは終了扱い
            to_end = [n.id for n in existing_qs if n.cast_id not in requested_cast_ids and n.ended_at is None]
            if to_end:
                BillCustomerNomination.objects.filter(id__in=to_end).update(ended_at=now)

            # 追加・復帰分
            from .models import Cast
            created = []
            for cast_id in requested_cast_ids:
                existing = existing_by_cast.get(cast_id)
                if existing:
                    # 既存が終了していたら再開（履歴は残らないが現行整合を優先）
                    if existing.ended_at is not None:
                        existing.started_at = now
                        existing.ended_at = None
                        existing.save(update_fields=["started_at", "ended_at", "updated_at"])
                    continue

                try:
                    cast = Cast.objects.get(id=cast_id)
                    nom = BillCustomerNomination.objects.create(
                        bill=bill,
                        customer_id=customer_id,
                        cast=cast,
                        started_at=now
                    )
                    created.append(nom)
                except Cast.DoesNotExist:
                    pass
            
            serializer = BillCustomerNominationSerializer(created, many=True)
            return Response({
                "results": serializer.data
            }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["delete"], url_path="nominations/(?P<nomination_id>[^/.]+)")
    def delete_nomination(self, request, pk=None, nomination_id=None):
        """
        特定の Nomination を削除
        
        DELETE /api/billing/bills/{bill_id}/nominations/{nomination_id}/
        """
        from .models import BillCustomerNomination
        
        bill = self.get_object()
        
        try:
            nom = BillCustomerNomination.objects.get(id=nomination_id, bill=bill)
            if nom.ended_at is None:
                nom.ended_at = timezone.now()
                nom.save(update_fields=["ended_at", "updated_at"])
            return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)
        except BillCustomerNomination.DoesNotExist:
            return Response(
                {"error": "Nomination not found"},
                status=status.HTTP_404_NOT_FOUND
            )


# ────────────────────────────────────────────────────────────────────
# BillCustomer nested endpoint（arrived_at/left_at更新用）
# ────────────────────────────────────────────────────────────────────
class BillCustomerViewSet(viewsets.ModelViewSet):
    """
    BillCustomer（伝票内の顧客）を管理
    
    PATCH /api/billing/bill-customers/{id}/ で arrived_at/left_at を更新可能
    """
    serializer_class = None  # 後で定義
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        from .models import BillCustomer
        return (
            BillCustomer.objects
            .select_related("bill", "bill__table", "customer")
            .filter(bill__table__store_id=sid)
        )
    
    def get_serializer_class(self):
        from .serializers_timeline import BillCustomerSerializer
        return BillCustomerSerializer
    
    def perform_update(self, serializer):
        serializer.save()


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
class CastViewSet(StoreScopedModelViewSet):
    queryset = Cast.objects.select_related("store").prefetch_related("category_rates")
    serializer_class = CastSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["user__is_active", "stage_name", "user__username"]
    search_fields = ["stage_name", "user__username", "user__first_name", "user__last_name"]

    @action(detail=True, methods=['get','post'], url_path='goals')
    def goals(self, request, pk=None):
        """
        GET  /billing/casts/{id}/goals/       : 目標一覧（active=1/0 フィルタ可）
        POST /billing/casts/{id}/goals/       : 目標作成
        """
        cast = self.get_object()

        if request.method == 'GET':
            qs = cast.goals.all().order_by('-active','-updated_at','-created_at')
            active = request.query_params.get('active')
            if active in ('0','1','true','false','True','False'):
                qs = qs.filter(active=active in ('1','true','True'))
            ser = CastGoalSerializer(qs, many=True)
            return Response(ser.data)

        # POST
        if not _can_edit_cast_goals(request.user, cast):
            return Response({'detail':'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        data.pop('cast', None)  # URLで束縛
        ser = CastGoalSerializer(data=data, context={'cast': cast})
        if ser.is_valid():
            obj = ser.save(cast=cast)
            # 必要ならここで obj.record_new_hits() を呼んで通知発火へ
            return Response(CastGoalSerializer(obj).data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get','patch','delete'], url_path=r'goals/(?P<goal_id>\d+)')
    def goal_detail(self, request, pk=None, goal_id=None):
        """
        GET    /billing/casts/{id}/goals/{goal_id}/
        PATCH  /billing/casts/{id}/goals/{goal_id}/   （target/period/active の軽微な更新のみ）
        DELETE /billing/casts/{id}/goals/{goal_id}/   （archive：active=False）
        """
        cast = self.get_object()
        try:
            goal = cast.goals.get(pk=goal_id)
        except CastGoal.DoesNotExist:
            return Response({'detail':'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            return Response(CastGoalSerializer(goal).data)

        if not _can_edit_cast_goals(request.user, cast):
            return Response({'detail':'forbidden'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'DELETE':
            goal.active = False
            goal.save(update_fields=['active','updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        allowed = {'target_value','period_kind','start_date','end_date','active'}
        payload = {k:v for k,v in request.data.items() if k in allowed}
        ser = CastGoalSerializer(goal, data=payload, partial=True, context={'cast': cast})
        if ser.is_valid():
            obj = ser.save()
            return Response(CastGoalSerializer(obj).data)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class CastPayoutListView(generics.ListAPIView):
    serializer_class = CastPayoutListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class  = CastPayoutFilter

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        qs = (CastPayout.objects
              .select_related("cast", "bill", "bill__table", "bill_item", "bill_item__item_master")
              .prefetch_related("bill__stays")                          # ← stay_type 計算のため
              .filter(bill__isnull=False, bill__table__store_id=sid))
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


class BillTagViewSet(NoStoreListMixin, StoreScopedModelViewSet):
    queryset = BillTag.objects.all()
    serializer_class = BillTagSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_active']


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
    serializer_class  = StaffSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends   = [DjangoFilterBackend, SearchFilter]
    filterset_fields  = ["stores", "role"]
    search_fields     = ["user__username","user__first_name","user__last_name","user__email"]

    def get_queryset(self):
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        qs = (Staff.objects
              .filter(stores__id=sid)
              .prefetch_related("stores", "user")
              .distinct())

        # role フィルタ（例: ?role=mgr で店長のみ）
        role = (self.request.query_params.get("role") or "").strip()
        if role:
            qs = qs.filter(role=role)

        # ★ 手動フィルタ（SearchFilter保険）
        kw = (self.request.query_params.get("search")
              or self.request.query_params.get("q")
              or self.request.query_params.get("name"))
        if kw:
            kw = kw.strip()
            if kw:
                qs = qs.filter(
                    Q(user__username__icontains=kw) |
                    Q(user__first_name__icontains=kw) |
                    Q(user__last_name__icontains=kw)  |
                    Q(user__email__icontains=kw)
                ).distinct()
        return qs
    

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
    /api/customers/?q= 検索（氏名・あだ名・電話・棚番号）
    /api/customers/?has_bottle=true マイボトル有り顧客のみ
    /api/customers/?bottle_shelf=A-12 特定の棚番号で検索
    ※ 現状グローバル。将来は store FK 追加を検討。
    """
    queryset = Customer.objects.all().order_by("-updated_at")
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # display_name がない（full_name と alias の両方が空）顧客を除外
        # ただし、一覧表示（list）と相性チェック（match）の時のみ
        # 個別取得（retrieve）や他のアクションでは全て表示
        if self.action in ['list', 'match_ranking']:
            qs = qs.exclude(Q(full_name='') & Q(alias=''))
        
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(alias__icontains=q) |
                Q(phone__icontains=q) |
                Q(bottle_shelf__icontains=q)
            )
        
        # タグフィルタ（tag_code=vip&tag_code=regular のような複数指定対応）
        tag_codes = self.request.query_params.getlist("tag_code")
        if tag_codes:
            qs = qs.filter(tags__code__in=tag_codes).distinct()
        
        # マイボトルフィルタ
        has_bottle = self.request.query_params.get("has_bottle")
        if has_bottle is not None:
            qs = qs.filter(has_bottle=(has_bottle.lower() == 'true'))
        
        # 棚番号フィルタ
        bottle_shelf = self.request.query_params.get("bottle_shelf")
        if bottle_shelf:
            qs = qs.filter(bottle_shelf__icontains=bottle_shelf)
        
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

    @action(detail=False, methods=["get"], url_path='match')
    def match_ranking(self, request):
        """
        キャスト向け：顧客×キャスト相性ランキング
        GET /api/billing/customers/match/?cast_id=<id>&sort=spent_30d&min_spent_30d=10000&limit=20
        
        Phase1: BillItem.served_by_cast が付いた明細のみを「そのキャストの売上」とみなす
        """
        cast_id = request.query_params.get('cast_id')
        if not cast_id:
            return Response({'error': 'cast_id is required'}, status=400)
        
        try:
            cast = Cast.objects.get(id=cast_id)
        except Cast.DoesNotExist:
            return Response({'error': 'Cast not found'}, status=404)
        
        # Store-Locked: request.store で絞り込み
        store = getattr(request, 'store', None)
        if not store:
            return Response({'error': 'Store not found'}, status=400)
        
        # 顧客×キャスト相性集計
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # BillItem 起点で Customer ごとに集計
        # 名前なし顧客を除外（full_name と alias の両方が空の顧客）
        customers_with_stats = Customer.objects.filter(
            bills__table__store=store,
            bills__items__served_by_cast_id=cast_id
        ).exclude(
            Q(full_name='') & Q(alias='')
        ).annotate(
            # 通算売上（served_by_cast 付き明細の price * qty 合計）
            spent_with_cast_total=Coalesce(
                Sum(
                    F('bills__items__price') * F('bills__items__qty'),
                    filter=Q(bills__items__served_by_cast_id=cast_id) & Q(bills__table__store=store)
                ),
                0
            ),
            
            # 直近30日売上
            spent_with_cast_30d=Coalesce(
                Sum(
                    F('bills__items__price') * F('bills__items__qty'),
                    filter=Q(bills__items__served_by_cast_id=cast_id) & 
                           Q(bills__table__store=store) & 
                           Q(bills__opened_at__gte=thirty_days_ago)
                ),
                0
            ),
            
            # served_by_cast 付き明細件数
            served_item_count=Count('bills__items', 
                                   filter=Q(bills__items__served_by_cast_id=cast_id) & Q(bills__table__store=store)),
            
            # served_by_cast 付き明細が含まれる伝票数（distinct bill）
            served_bill_count=Count('bills', 
                                   filter=Q(bills__items__served_by_cast_id=cast_id) & Q(bills__table__store=store),
                                   distinct=True),
            
            # 最後に served_by_cast が発生した日時（opened_at 基準）
            last_served_at=Max('bills__opened_at', 
                              filter=Q(bills__items__served_by_cast_id=cast_id) & Q(bills__table__store=store)),
            
            # Customer全体 stats（参考）
            visit_count=Count('bills', filter=Q(bills__table__store=store), distinct=True),
            total_spent=Coalesce(Sum('bills__grand_total', filter=Q(bills__table__store=store)), 0),
            last_visit_at=Max('bills__opened_at', filter=Q(bills__table__store=store))
        ).distinct()
        
        # フィルタ適用
        min_spent_30d = request.query_params.get('min_spent_30d')
        if min_spent_30d:
            customers_with_stats = customers_with_stats.filter(spent_with_cast_30d__gte=int(min_spent_30d))
        
        min_spent_total = request.query_params.get('min_spent_total')
        if min_spent_total:
            customers_with_stats = customers_with_stats.filter(spent_with_cast_total__gte=int(min_spent_total))
        
        min_served_bill_count = request.query_params.get('min_served_bill_count')
        if min_served_bill_count:
            customers_with_stats = customers_with_stats.filter(served_bill_count__gte=int(min_served_bill_count))
        
        # ソート
        sort_param = request.query_params.get('sort', 'spent_30d')
        sort_map = {
            'spent_30d': '-spent_with_cast_30d',
            'spent_total': '-spent_with_cast_total',
            'last_served': '-last_served_at',
            'served_bill_count': '-served_bill_count',
        }
        order_by = sort_map.get(sort_param, '-spent_with_cast_30d')
        customers_with_stats = customers_with_stats.order_by(order_by)
        
        # リミット
        limit = int(request.query_params.get('limit', 20))
        limit = min(limit, 100)  # 上限100
        customers_with_stats = customers_with_stats[:limit]
        
        # レスポンス構築
        results = []
        for customer in customers_with_stats:
            spent_total = int(customer.spent_with_cast_total or 0)
            spent_30d = int(customer.spent_with_cast_30d or 0)
            bill_count = int(customer.served_bill_count or 0)
            
            results.append({
                'customer': CustomerSerializer(customer).data,
                'stats': {
                    'visit_count': int(customer.visit_count or 0),
                    'total_spent': int(customer.total_spent or 0),
                    'last_visit_at': customer.last_visit_at,
                },
                'affinity': {
                    'cast_id': int(cast_id),
                    'spent_with_cast_total': spent_total,
                    'spent_with_cast_30d': spent_30d,
                    'served_item_count': int(customer.served_item_count or 0),
                    'served_bill_count': bill_count,
                    'last_served_at': customer.last_served_at,
                    'avg_spent_per_bill_with_cast': int(spent_total / bill_count) if bill_count > 0 else 0,
                }
            })
        
        return Response({
            'cast': CastSerializer(cast).data,
            'count': len(results),
            'results': results,
        })

    @action(detail=True, methods=["get"], url_path='affinity')
    def affinity(self, request, pk=None):
        """
        顧客個別：特定キャストとの相性
        GET /api/billing/customers/<customer_id>/affinity/?cast_id=<id>
        """
        cast_id = request.query_params.get('cast_id')
        if not cast_id:
            return Response({'error': 'cast_id is required'}, status=400)
        
        try:
            cast = Cast.objects.get(id=cast_id)
        except Cast.DoesNotExist:
            return Response({'error': 'Cast not found'}, status=404)
        
        customer = self.get_object()
        
        # Store-Locked: request.store で絞り込み
        store = getattr(request, 'store', None)
        if not store:
            return Response({'error': 'Store not found'}, status=400)
        
        # 顧客×キャスト相性集計
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # BillItem から集計
        items = BillItem.objects.filter(
            bill__customers=customer,
            bill__table__store=store,
            served_by_cast_id=cast_id
        )
        
        spent_with_cast_total = sum((item.price or 0) * item.qty for item in items)
        
        items_30d = items.filter(bill__opened_at__gte=thirty_days_ago)
        spent_with_cast_30d = sum((item.price or 0) * item.qty for item in items_30d)
        
        served_item_count = items.count()
        served_bill_count = items.values('bill').distinct().count()
        
        last_served_bill = items.order_by('-bill__opened_at').first()
        last_served_at = last_served_bill.bill.opened_at if last_served_bill else None
        
        # Customer全体 stats
        customer_bills = Bill.objects.filter(customers=customer, table__store=store)
        visit_count = customer_bills.count()
        total_spent = customer_bills.aggregate(total=Sum('grand_total'))['total'] or 0
        last_visit = customer_bills.order_by('-opened_at').first()
        last_visit_at = last_visit.opened_at if last_visit else None
        
        return Response({
            'customer': CustomerSerializer(customer).data,
            'cast': CastSerializer(cast).data,
            'stats': {
                'visit_count': int(visit_count),
                'total_spent': int(total_spent),
                'last_visit_at': last_visit_at,
            },
            'affinity': {
                'cast_id': int(cast_id),
                'spent_with_cast_total': int(spent_with_cast_total),
                'spent_with_cast_30d': int(spent_with_cast_30d),
                'served_item_count': int(served_item_count),
                'served_bill_count': int(served_bill_count),
                'last_served_at': last_served_at,
                'avg_spent_per_bill_with_cast': int(spent_with_cast_total / served_bill_count) if served_bill_count > 0 else 0,
            }
        })


# ────────────────────────────────────────────────────────────────────
# 店舗お知らせ（StoreNotice）— 自店ロック
# ────────────────────────────────────────────────────────────────────
class NewsPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


# ────────────────────────────────────────────────────────────────────
# 顧客タグ管理 & 集計
# ────────────────────────────────────────────────────────────────────
class CustomerTagViewSet(viewsets.ModelViewSet):
    """
    顧客タグマスター
    - GET  /api/customer-tags/         一覧（customer_count付き）
    - GET  /api/customer-tags/<id>/    詳細（customer_count付き）
    - POST /api/customer-tags/         作成
    - PUT/PATCH/DELETE も可
    """
    queryset = CustomerTag.objects.all().order_by('code')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        # create/update は共通の CustomerTagSerializer を使用
        if self.action in ('create', 'update', 'partial_update'):
            return CustomerTagSerializer

        # list/retrieve は customer_count を返す派生シリアライザ
        class CustomerTagWithCountSerializer(CustomerTagSerializer):
            customer_count = serializers.SerializerMethodField()

            class Meta(CustomerTagSerializer.Meta):
                fields = CustomerTagSerializer.Meta.fields + ('description', 'customer_count', 'created_at')

            def get_customer_count(self, obj):
                return obj.customers.count()

        return CustomerTagWithCountSerializer



class CustomerTagAnalyticsView(APIView):
    """
    顧客属性別の詳細分析API
    GET /api/customer-analytics/by-tag/?tag_code=vip
    
    レスポンス:
    {
      "tag": {...},
      "customers": [{id, alias, full_name, visit_count, total_spent, ...}, ...],
      "summary": {
        "total_customers": 42,
        "total_visits": 215,
        "total_revenue": 8500000,
        "avg_revenue_per_customer": 202380,
      }
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import CustomerTag, BillCustomer
        from django.db.models import Count, Sum
        
        tag_code = request.query_params.get("tag_code")
        if not tag_code:
            return Response(
                {"error": "tag_code parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tag = get_object_or_404(CustomerTag, code=tag_code, is_active=True)
        customers = tag.customers.all()
        
        # 顧客ごとの集計
        customer_stats = []
        total_visits = 0
        total_revenue = 0
        
        for cust in customers:
            visits = BillCustomer.objects.filter(customer=cust).count()
            revenue = sum(
                bill.grand_total for bill in cust.bills.all()
            )
            
            total_visits += visits
            total_revenue += revenue
            
            customer_stats.append({
                'id': cust.id,
                'alias': cust.alias or cust.full_name,
                'full_name': cust.full_name,
                'phone': cust.phone,
                'visit_count': visits,
                'total_spent': revenue,
                'last_visited': (
                    cust.bills.order_by('-closed_at')
                    .values_list('closed_at', flat=True)
                    .first()
                    .date().isoformat() if cust.bills.exists() else None
                ),
            })
        
        return Response({
            'tag': {
                'id': tag.id,
                'code': tag.code,
                'name': tag.name,
                'color': tag.color,
            },
            'customers': customer_stats,
            'summary': {
                'total_customers': customers.count(),
                'total_visits': total_visits,
                'total_revenue': total_revenue,
                'avg_revenue_per_customer': (
                    int(total_revenue / customers.count())
                    if customers.count() > 0 else 0
                ),
            },
        })


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


# 既存：StoreScopedModelViewSet を継承して “自店だけ” に絞る
class StoreSeatSettingViewSet(StoreScopedModelViewSet):
    queryset = StoreSeatSetting.objects.all().select_related('store','seat_type')
    serializer_class = StoreSeatSettingSerializer
    filterset_fields = ['seat_type']  # 任意
    search_fields = ['memo']          # 任意


class DiscountRuleViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DiscountRuleSerializer
    queryset = DiscountRule.objects.all()

    def get_queryset(self):
        # ★ 既存の Store-Locked 決定ロジックだけを使う（グローバル変更なし）
        sid = StoreScopedModelViewSet.require_store(self, self.request)
        # 店舗のレコード + グローバル(null) を許可
        qs = DiscountRule.objects.filter(Q(store_id=sid) | Q(store__isnull=True))
        # 状態
        is_active = self.request.query_params.get('is_active')
        if is_active in ('1','true','True'):
            qs = qs.filter(is_active=True)
        # 基本フラグ
        is_basic = self.request.query_params.get('is_basic')
        if is_basic in ('1','true','True'):
            qs = qs.filter(is_basic=True)
        # 表示場所
        place = self.request.query_params.get('place')  # basics | pay
        if place == 'basics':
            qs = qs.filter(show_in_basics=True)
        elif place == 'pay':
            qs = qs.filter(show_in_pay=True)

        # code/name 検索
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))

        return qs.order_by('store_id', 'sort_order', '-created_at')



# === 給与計算 ===


def _get_store_id_from_header(request):
    # Store-Locked: ミドルウェアで検証済みでも、ここで参照してフィルタ
    sid = request.META.get("HTTP_X_STORE_ID")
    if not sid:
        raise ValueError("X-Store-Id header is required")
    return int(sid)

def _get_range(request):
    df = request.query_params.get("from")
    dt = request.query_params.get("to")
    if not (df and dt):
        today = date.today()
        df = today.replace(day=1).isoformat()
        dt = today.isoformat()
    return df, dt

class CastPayrollSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sid = _get_store_id_from_header(request)
        df, dt = _get_range(request)

        # --- Subquery: commission（CastPayout合計） ---
        commission_sq = (
            CastPayout.objects
            .filter(
                cast_id=OuterRef('pk'),
                bill__table__store_id=sid,
                bill__closed_at__date__range=(df, dt),
            )
            .values('cast')           # グルーピングキー
            .annotate(total=Sum('amount'))
            .values('total')[:1]
        )

        # --- Subquery: hourly_pay & worked_min（CastDailySummary合計） ---
        hourly_sq = (
            CastDailySummary.objects
            .filter(
                cast_id=OuterRef('pk'),
                store_id=sid,
                work_date__range=(df, dt),
            )
            .values('cast')
            .annotate(total=Sum('payroll'))
            .values('total')[:1]
        )

        worked_min_sq = (
            CastDailySummary.objects
            .filter(
                cast_id=OuterRef('pk'),
                store_id=sid,
                work_date__range=(df, dt),
            )
            .values('cast')
            .annotate(total=Sum('worked_min'))
            .values('total')[:1]
        )

        qs = (
            Cast.objects.filter(store_id=sid)
            .annotate(
                commission = Coalesce(Subquery(commission_sq), Value(0), output_field=IntegerField()),
                hourly_pay = Coalesce(Subquery(hourly_sq),     Value(0), output_field=IntegerField()),
                worked_min = Coalesce(Subquery(worked_min_sq), Value(0), output_field=IntegerField()),
            )
            .values('id', 'stage_name', 'worked_min', 'hourly_pay', 'commission')
            .order_by('stage_name', 'id')
        )

        data = []
        for r in qs:
            worked_min = int(r['worked_min'] or 0)
            hourly_pay = int(r['hourly_pay'] or 0)
            commission = int(r['commission'] or 0)
            data.append({
                'id': r['id'],
                'stage_name': r['stage_name'],
                'worked_min': worked_min,
                'total_hours': round(worked_min / 60.0, 2),
                'hourly_pay': hourly_pay,
                'commission': commission,
                'total': hourly_pay + commission,   # 合計＝歩合＋時給のみ
            })

        ser = CastPayrollSummaryRowSerializer(data, many=True)
        return Response(ser.data)
    
    

class CastPayrollDetailView(APIView):
    """
    GET /api/billing/payroll/casts/<cast_id>/?from=YYYY-MM-DD&to=YYYY-MM-DD
    レスポンス:
    {
      cast: {id, stage_name},
      range: {from,to},
      shifts: [{id, clock_in, clock_out, worked_min, hourly_wage_snap, payroll_amount}, ...],
      payouts: [{id, amount, bill:{id,closed_at}, bill_item:{id,name,price,qty}}, ...],
      totals: { total_hours, hourly_pay, commission, total }
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, cast_id: int):
        sid = _get_store_id_from_header(request)
        df, dt = _get_range(request)

        # シフト（時給）明細
        shifts = (
            CastShift.objects
            .filter(cast_id=cast_id, store_id=sid, clock_in__date__range=(df, dt))
            .values("id", "clock_in", "clock_out", "worked_min", "hourly_wage_snap", "payroll_amount")
            .order_by("clock_in", "id")
        )
        shifts_list = list(shifts)

        # 歩合（伝票由来）明細
        payouts_qs = (
            CastPayout.objects
            .filter(cast_id=cast_id, bill__table__store_id=sid, bill__closed_at__date__range=(df, dt))
            .select_related("bill", "bill_item")
            .order_by("id")
        )
        payouts = CastPayoutDetailSerializer(payouts_qs, many=True).data

        # トータル
        total_hours = round(sum(int(s.get("worked_min") or 0) for s in shifts_list) / 60.0, 2)
        hourly_pay  = sum(int(s.get("payroll_amount") or 0) for s in shifts_list)
        commission  = sum(int(p.get("amount") or 0) for p in payouts)
        total       = hourly_pay + commission

        cast_obj = Cast.objects.filter(id=cast_id, store_id=sid).first()
        return Response({
            "cast"   : CastMiniSerializer(cast_obj).data if cast_obj else None,
            "range"  : {"from": df, "to": dt},
            "shifts" : shifts_list,
            "payouts": payouts,
            "totals" : {
                "total_hours": total_hours,
                "hourly_pay" : hourly_pay,
                "commission" : commission,
                "total"      : total,
            },
        })




class CastPayrollDetailCSVView(APIView):
    """
    GET /api/billing/payroll/casts/<cast_id>/export.csv?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, cast_id: int):
        sid = _get_store_id_from_header(request)
        df, dt = _get_range(request)

        # 明細はJSONの詳細APIと同じロジック
        shifts = (
            CastShift.objects
            .filter(cast_id=cast_id, store_id=sid, clock_in__date__range=(df, dt))
            .values("id","clock_in","clock_out","worked_min","hourly_wage_snap","payroll_amount")
            .order_by("clock_in","id")
        )
        payouts_qs = (
            CastPayout.objects
            .filter(cast_id=cast_id, bill__table__store_id=sid, bill__closed_at__date__range=(df, dt))
            .select_related("bill","bill_item")
            .order_by("id")
        )

        # 合計
        total_hours = round(sum(int(s.get("worked_min") or 0) for s in shifts) / 60.0, 2)
        hourly_pay  = sum(int(s.get("payroll_amount") or 0) for s in shifts)
        commission  = sum(int(getattr(p, "amount", 0)) for p in payouts_qs)
        total       = hourly_pay + commission
        cast_obj    = Cast.objects.filter(id=cast_id, store_id=sid).first()
        cast_name   = getattr(cast_obj, "stage_name", f"cast-{cast_id}")

        # CSV作成（BOM付きでExcel想定）
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["給与明細（キャスト）", cast_name])
        writer.writerow(["期間", f"{df} ～ {dt}"])
        writer.writerow(["総勤務時間(h)", total_hours, "時給合計", hourly_pay, "歩合", commission, "総額", total])
        writer.writerow([])

        # 明細（行を揃える）
        writer.writerow(["区分","出勤","退勤","勤務分","時給","時給額","伝票ID","明細ID","歩合額"])
        # シフト行
        for s in shifts:
            writer.writerow([
                "シフト",
                s.get("clock_in") or "",
                s.get("clock_out") or "",
                s.get("worked_min") or 0,
                s.get("hourly_wage_snap") or 0,
                s.get("payroll_amount") or 0,
                "", "", ""
            ])
        # 歩合行
        for p in payouts_qs:
            writer.writerow([
                "歩合", "", "", "", "", "",
                getattr(p.bill, "id", ""),
                getattr(p.bill_item, "id", ""),
                getattr(p, "amount", 0),
            ])

        csv_data = buf.getvalue()
        buf.close()

        resp = HttpResponse(
            content="\ufeff" + csv_data,  # UTF-8 BOM
            content_type="text/csv; charset=utf-8",
        )
        filename = f"payroll_{cast_name}_{df}_to_{dt}.csv"
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


# ═══════════════════════════════════════════════════════════════════
# 時間別売上サマリ API
# ═══════════════════════════════════════════════════════════════════
from .models import HourlySalesSummary, Store
from .serializers import HourlySalesSummarySerializer
from decimal import Decimal

class HourlySalesView(ListAPIView):
    """
    時間別売上サマリ取得API
    
    クエリパラメータ:
    - store_id: 店舗ID (必須, X-Store-Idヘッダーからも取得可)
    - date: 日付 (YYYY-MM-DD形式, 省略時は当日)
    - business_hours_only: true の場合は営業時間内のみ（0埋めしない）
    
    レスポンス: 0時～23時の24件のデータ配列（データがない時間帯も含む）
    各時間帯にキャスト別内訳(cast_breakdown)を含む
    is_within_business_hours: 営業時間内かどうか
    """
    serializer_class = HourlySalesSummarySerializer
    pagination_class = None  # 24件固定なのでページネーション不要

    def get_queryset(self):
        # store_idの取得（クエリパラメータ or ヘッダー）
        store_id = self.request.query_params.get('store_id')
        if not store_id:
            store_id = self.request.META.get('HTTP_X_STORE_ID') or self.request.META.get('HTTP_X_STORE_Id')
        
        if not store_id:
            raise ValidationError({'store_id': '店舗IDが必要です（クエリパラメータまたはX-Store-Idヘッダー）'})
        
        # 日付の取得（省略時は当日）
        date_str = self.request.query_params.get('date')
        if date_str:
            try:
                target_date = date.fromisoformat(date_str)
            except ValueError:
                raise ValidationError({'date': '日付はYYYY-MM-DD形式で指定してください'})
        else:
            target_date = timezone.now().date()

        # 時間別サマリを取得（0-23時の全時間帯、存在しない時間は空データ）
        qs = HourlySalesSummary.objects.filter(
            store_id=store_id,
            date=target_date
        ).prefetch_related(
            'cast_breakdown__cast'
        ).order_by('hour')

        return qs
    
    def list(self, request, *args, **kwargs):
        """0-23時の全時間帯を保証するカスタムlist"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # 既存データを時間別に格納
        data_by_hour = {item['hour']: item for item in serializer.data}
        
        # 0-23時の全時間帯を保証（データがない時間帯はゼロ埋め）
        store_id = request.query_params.get('store_id')
        if not store_id:
            store_id = request.META.get('HTTP_X_STORE_ID') or request.META.get('HTTP_X_STORE_Id')
        
        date_str = request.query_params.get('date')
        if date_str:
            target_date = date.fromisoformat(date_str)
        else:
            target_date = timezone.now().date()
        
        business_hours_only = request.query_params.get('business_hours_only', 'false').lower() == 'true'
        store = Store.objects.get(id=int(store_id))
        
        result = []
        for h in range(24):
            # 営業時間かどうか判定（営業日ベース）
            hour_relative = Decimal(str(h))
            if h < store.business_day_cutoff_hour:
                hour_relative += 24
            is_within_hours = store.business_open_hour <= hour_relative <= store.business_close_hour
            
            # business_hours_only=true の場合は営業時間外はスキップ
            if business_hours_only and not is_within_hours:
                continue
            
            if h in data_by_hour:
                result.append(data_by_hour[h])
            else:
                # データがない時間帯はゼロ埋め
                result.append({
                    'id': None,
                    'store': int(store_id),
                    'store_name': store.name,
                    'date': target_date.isoformat(),
                    'hour': h,
                    'time_display': f'{h:02d}:00',
                    'sales_total': 0,
                    'bill_count': 0,
                    'customer_count': 0,
                    'sales_set': 0,
                    'sales_drink': 0,
                    'sales_food': 0,
                    'sales_champagne': 0,
                    'cast_breakdown': [],
                    'is_within_business_hours': is_within_hours,
                    'business_hours_display': store.business_hours_display,
                    'updated_at': None
                })
        
        return Response(result)


# ═══════════════════════════════════════════════════════════════════
# 給与締め（PayrollRun）API
# ═══════════════════════════════════════════════════════════════════

from dateutil.relativedelta import relativedelta
from .models import PayrollRun, PayrollRunLine, PayrollRunBackRow


def get_default_payroll_period(store, ref_date=None):
    """
    storeの締め設定から「ref_dateを含む期間」を返す
    
    Args:
        store: Store インスタンス
        ref_date: 基準日（省略時は今日）
    
    Returns:
        (start_date, end_date) のタプル
    """
    if ref_date is None:
        ref_date = date.today()
    
    if store.payroll_cutoff_kind == Store.PAYROLL_CUTOFF_EOM:
        # 月末締め: 当月1日～当月末日
        start_date = ref_date.replace(day=1)
        # 月末を取得: 翌月1日 - 1日
        if ref_date.month == 12:
            end_date = date(ref_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(ref_date.year, ref_date.month + 1, 1) - timedelta(days=1)
        return (start_date, end_date)
    
    # 日付締め（例: 25締め）
    cutoff_day = store.payroll_cutoff_day or 25
    
    if ref_date.day < cutoff_day:
        # 例: 2025-01-15 で 25締めなら、前月25～当月24
        # start: 2024-12-25
        # end: 2025-01-24
        start_date = (ref_date.replace(day=1) - timedelta(days=1)).replace(day=cutoff_day)
        end_date = ref_date.replace(day=cutoff_day) - timedelta(days=1)
    else:
        # 例: 2025-01-28 で 25締めなら、当月25～翌月24
        # start: 2025-01-25
        # end: 2025-02-24
        start_date = ref_date.replace(day=cutoff_day)
        next_month = ref_date + relativedelta(months=1)
        end_date = next_month.replace(day=cutoff_day) - timedelta(days=1)
    
    return (start_date, end_date)


def check_overlap(store, period_start, period_end):
    """
    既存の PayrollRun と重複があれば True を返す
    
    Args:
        store: Store インスタンス
        period_start: 新しい期間の開始日
        period_end: 新しい期間の終了日
    
    Returns:
        bool: 重複があれば True
    """
    overlap_qs = PayrollRun.objects.filter(
        store=store,
        period_start__lte=period_end,
        period_end__gte=period_start,
    )
    return overlap_qs.exists()


class PayrollRunPreviewView(APIView):
    """
    GET /api/billing/payroll/runs/preview/?from=YYYY-MM-DD&to=YYYY-MM-DD
    
    権限: user_manage (Manager専用)
    
    レスポンス:
    {
      "range": {"from": "...", "to": "..."},
      "overlap": true/false,
      "summary": [
        {
          "cast_id": 123,
          "stage_name": "...",
          "worked_min": 1200,
          "hourly_pay": 12000,
          "commission": 50000,
          "total": 62000
        },
        ...
      ]
    }
    """
    permission_classes = [IsAuthenticated, RequireCap]
    required_cap = 'user_manage'

    def get(self, request):
        sid = _get_store_id_from_header(request)
        store = get_object_or_404(Store, pk=sid)

        # 期間
        from_param = request.query_params.get('from')
        to_param = request.query_params.get('to')
        if from_param and to_param:
            df = from_param
            dt = to_param
        else:
            ref_date = date.today()
            df, dt = get_default_payroll_period(store, ref_date)
            df = df.isoformat()
            dt = dt.isoformat()

        overlap = check_overlap(store, df, dt)

        # ── 伝票明細（キャスト別にグルーピング） ──
        bill_rows_map = defaultdict(dict)  # {cast_id: {bill_id: row}}
        sales_total_map = defaultdict(int)

        items_qs = (
            BillItem.objects
            .filter(
                bill__table__store_id=sid,
                bill__closed_at__date__range=(df, dt),
            )
            .select_related('bill', 'served_by_cast', 'item_master')
        )

        for it in items_qs:
            cast_id = it.served_by_cast_id
            if not cast_id:
                continue
            bill = it.bill
            if not bill:
                continue

            bill_id = bill.id
            row = bill_rows_map[cast_id].get(bill_id)
            if not row:
                row = {
                    'bill_id': bill_id,
                    'closed_at': bill.closed_at,
                    'sales': 0,
                    'back': 0,
                    'items': [],
                }
                bill_rows_map[cast_id][bill_id] = row

            price = int(it.price or 0)
            qty = int(it.qty or 0)
            subtotal = price * qty

            row['sales'] += subtotal
            sales_total_map[cast_id] += subtotal

            row['items'].append({
                'name': (getattr(it, 'name', None) or getattr(it.item_master, 'name', '') or ''),
                'qty': qty,
                'price': price,
            })

        payouts_qs = (
            CastPayout.objects
            .filter(
                bill__table__store_id=sid,
                bill__closed_at__date__range=(df, dt),
            )
            .select_related('bill', 'cast')
        )

        for p in payouts_qs:
            cast_id = p.cast_id
            bill = p.bill
            if not cast_id or not bill:
                continue
            bill_id = bill.id

            row = bill_rows_map[cast_id].get(bill_id)
            if not row:
                row = {
                    'bill_id': bill_id,
                    'closed_at': bill.closed_at,
                    'sales': 0,
                    'back': 0,
                    'items': [],
                }
                bill_rows_map[cast_id][bill_id] = row

            row['back'] += int(p.amount or 0)

        bill_rows_sorted = {}
        for cid, bills in bill_rows_map.items():
            bill_rows_sorted[cid] = sorted(
                bills.values(),
                key=lambda b: (b.get('closed_at') or timezone.make_aware(timezone.datetime.min), b.get('bill_id') or 0)
            )

        # ── 給与集計（既存の集計ロジック） ──
        commission_sq = (
            CastPayout.objects
            .filter(
                cast_id=OuterRef('pk'),
                bill__table__store_id=sid,
                bill__closed_at__date__range=(df, dt),
            )
            .values('cast')
            .annotate(total=Sum('amount'))
            .values('total')[:1]
        )

        hourly_sq = (
            CastDailySummary.objects
            .filter(
                cast_id=OuterRef('pk'),
                store_id=sid,
                work_date__range=(df, dt),
            )
            .values('cast')
            .annotate(total=Sum('payroll'))
            .values('total')[:1]
        )

        worked_min_sq = (
            CastDailySummary.objects
            .filter(
                cast_id=OuterRef('pk'),
                store_id=sid,
                work_date__range=(df, dt),
            )
            .values('cast')
            .annotate(total=Sum('worked_min'))
            .values('total')[:1]
        )

        qs = (
            Cast.objects.filter(store_id=sid)
            .annotate(
                commission=Coalesce(Subquery(commission_sq), Value(0), output_field=IntegerField()),
                hourly_pay=Coalesce(Subquery(hourly_sq), Value(0), output_field=IntegerField()),
                worked_min=Coalesce(Subquery(worked_min_sq), Value(0), output_field=IntegerField()),
            )
            .values('id', 'stage_name', 'worked_min', 'hourly_pay', 'commission')
            .order_by('stage_name', 'id')
        )

        summary = []
        for r in qs:
            cast_id = r['id']
            worked_min = int(r['worked_min'] or 0)
            hourly_pay = int(r['hourly_pay'] or 0)
            commission = int(r['commission'] or 0)

            summary.append({
                'cast_id': cast_id,
                'stage_name': r['stage_name'],
                'worked_min': worked_min,
                'hourly_pay': hourly_pay,
                'commission': commission,
                'total': hourly_pay + commission,
                'sales_total': int(sales_total_map.get(cast_id, 0)),
                'bill_rows': bill_rows_sorted.get(cast_id, []),
            })

        # --- PayrollRun を期間に応じて get_or_create し、run_id を返す ---
        ps = date.fromisoformat(df) if isinstance(df, str) else df
        pe = date.fromisoformat(dt) if isinstance(dt, str) else dt

        run, _created = PayrollRun.objects.get_or_create(
            store=store,
            period_start=ps,
            period_end=pe,
            defaults={
                "created_by": request.user if getattr(request.user, "is_authenticated", False) else None,
                "overlap_warning": overlap,
                "note": "",
            },
        )
        # 既存runがあり overlap_warning を最新化したい場合は更新
        if run.overlap_warning != overlap:
            run.overlap_warning = overlap
            run.save(update_fields=["overlap_warning"])

        return Response({
            'range': {'from': df, 'to': dt},
            'overlap': overlap,
            'run_id': run.id,
            'summary': summary,
        })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Personnel Expense ViewSets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PersonnelExpenseCategoryViewSet(StoreScopedModelViewSet):
    """人件費経費カテゴリ（店舗ごと）"""
    queryset = PersonnelExpenseCategory.objects.all()
    serializer_class = PersonnelExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated, RequireCap]
    required_cap = 'operate_orders'
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['code', 'name']
    filterset_fields = ['is_active']


class PersonnelExpenseViewSet(StoreScopedModelViewSet):
    """人件費経費（cast/staff/managerの立替/店舗負担）"""
    queryset = PersonnelExpense.objects.select_related(
        'store', 'category', 'subject_user', 'payroll_run'
    ).all()
    serializer_class = PersonnelExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, RequireCap]
    required_cap = 'operate_orders'
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['subject_user__username', 'description']
    filterset_fields = ['status', 'policy', 'subject_role', 'category', 'payroll_run']

    def get_queryset(self):
        qs = super().get_queryset()

        qs = qs.annotate(
            settled_amount_db=Coalesce(
                Sum('settlement_events__amount'),
                Value(0),
                output_field=IntegerField(),
            ),
        ).annotate(
            remaining_amount_db=F('amount') - F('settled_amount_db')
        )

        role = getattr(self.request.user, "current_role", None)
        if role != "manager":
            qs = qs.filter(subject_user=self.request.user)

        return qs

    def perform_create(self, serializer):
        role = getattr(self.request.user, "current_role", None)
        if role in ("cast", "staff"):
            # 非managerは勝手に他人を作れないよう強制
            serializer.save(
                store=self.request.store,
                subject_user=self.request.user,
                subject_role=role,
            )
        else:
            serializer.save(store=self.request.store)

    @action(detail=True, methods=['post'], url_path='settlements')
    def settlements(self, request, pk=None):
        """
        POST /personnel-expenses/{id}/settlements/
        SettlementEvent を作成し、残高が0になれば status を settled に
        """
        expense = self.get_object()
        
        # リクエストデータから amount, settled_at, note を取得
        serializer = PersonnelExpenseSettlementEventSerializer(
            data={
                'expense_id': expense.id,
                'amount': request.data.get('amount'),
                'settled_at': request.data.get('settled_at'),
                'note': request.data.get('note', ''),
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        
        # expense をリフレッシュして settled_amount を再計算
        expense.refresh_from_db()
        
        return Response({
            'event': serializer.data,
            'expense': PersonnelExpenseSerializer(expense, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)


@action(detail=True, methods=['post'], url_path='attach-personnel-expenses')
def attach_personnel_expenses_to_run(request, pk=None):
    """
    POST /payroll/runs/{run_id}/attach-personnel-expenses/
    PayrollRun に人件費経費を一括紐付け
    - payroll_run が null で occurred_at が期間内の expense を run に紐付け
    """
    # PayrollRun を取得（store チェック込み）
    store_id = getattr(request, 'store', None) and request.store.id
    if not store_id:
        raise ValidationError({'store': 'X-Store-Id header is required.'})
    
    try:
        run = PayrollRun.objects.get(pk=pk, store_id=store_id)
    except PayrollRun.DoesNotExist:
        raise ValidationError({'run_id': 'PayrollRun not found for this store.'})
    
    # 期間内の未紐付け経費を取得
    expenses = PersonnelExpense.objects.filter(
        store_id=store_id,
        payroll_run__isnull=True,
        occurred_at__gte=run.period_start,
        occurred_at__lt=run.period_end,
    )
    
    # 一括更新
    count = expenses.update(payroll_run=run)
    
    return Response({
        'run_id': run.id,
        'attached_count': count,
        'start_date': run.period_start,
        'end_date': run.period_end,
    }, status=status.HTTP_200_OK)
