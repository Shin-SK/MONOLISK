# billing/views.py

from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from django.conf      import settings
from django.apps      import apps
from rest_framework.generics import ListAPIView
from rest_framework    import viewsets, generics, permissions
from django.db.models import Sum, F, Q, IntegerField, ExpressionWrapper, Value
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models.functions import Coalesce
from datetime import date

from .models import Store, Table, Bill, ItemMaster, BillItem, CastPayout, Cast, BillCastStay, Cast, CastPayout ,BillItem, ItemCategory, CastShift, CastDailySummary
from .serializers import CastSalesSummarySerializer, CastPayoutDetailSerializer, CastItemDetailSerializer, CastSerializer, ItemCategorySerializer, StoreSerializer, TableSerializer, BillSerializer, ItemMasterSerializer, BillItemSerializer, CastSerializer, CastShiftSerializer, CastDailySummarySerializer, CastRankingSerializer
from .filters import CastPayoutFilter, CastItemFilter
from .services import get_cast_sales ,sync_nomination_fees


StoreModel = apps.get_model(settings.STORE_MODEL)    # billing.Store を取得

class StoreScopedModelViewSet(viewsets.ModelViewSet):
    """
    * GET   → 自店フィルタ
    * POST  → store を自動注入
    * PATCH → store フィールドは強制上書き
    """
    def _store(self, request):
        return getattr(request, 'store', None) or settings.DEFAULT_STORE_ID

    def get_queryset(self):
        qs = super().get_queryset()
        sid = self._store(self.request)
        if qs.model is Store:               # 店舗モデル自身だけは 1 件返す
            return qs.filter(pk=sid)
        if 'store_id' in [f.name for f in qs.model._meta.fields]:
            return qs.filter(store_id=sid)
        return qs

    def perform_create(self, serializer):
        sid = self._store(self.request)
        if 'store' in serializer.Meta.model._meta.fields_map:
            serializer.save(store_id=sid)
        else:
            serializer.save()

    def perform_update(self, serializer):
        sid = self._store(self.request)
        if 'store' in serializer.Meta.model._meta.fields_map:
            serializer.save(store_id=sid)
        else:
            serializer.save()



class StoreViewSet(StoreScopedModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        from django.conf import settings
        try:
            obj = Store.objects.get(pk=settings.DEFAULT_STORE_ID)
        except Store.DoesNotExist:
            return Response({'detail': 'default store not found'}, status=404)
        return Response(self.get_serializer(obj).data)


class ItemMasterViewSet(viewsets.ModelViewSet):
    queryset = ItemMaster.objects.select_related('category')   # ←追加
    serializer_class = ItemMasterSerializer



class TableViewSet(StoreScopedModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer




class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.prefetch_related('items')
    serializer_class = BillSerializer
    queryset = (
        Bill.objects.select_related('table__store')
        .prefetch_related('items', 'stays', 'nominated_casts')
        .order_by('-opened_at')
    )

    def get_queryset(self):
        qs   = Bill.objects.select_related('table__store').prefetch_related('items')
        user = self.request.user
        if user.is_staff or user.is_superuser or user.store_id is None:
            return qs
        return qs.filter(table__store_id=user.store_id)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        bill = self.get_object()

        with transaction.atomic():
            # ↓ ここでぜんぶ面倒を見る
            bill.close(settled_total=request.data.get('settled_total'))
        return Response(self.get_serializer(bill).data)
        

    @action(detail=True, methods=['post'], url_path='toggle-inhouse')
    def toggle_inhouse(self, request, pk=None):
        """
        cast_id と inhouse(bool) を受け取り、
        BillCastStay.stay_type を 'in' / 'free' に切り替える。
        さらに houseNom‑fee 行を差分同期する。
        """
        bill    = self.get_object()
        cid     = int(request.data.get('cast_id'))
        want_in = bool(request.data.get('inhouse'))

        # ① 変更前の inhouse ＆ main 集合をキャッシュ
        prev_in   = set(
            bill.stays.filter(stay_type='in', left_at__isnull=True)
                .values_list('cast_id', flat=True)
        )
        prev_main = set(bill.nominated_casts.values_list('id', flat=True))

        stay, _ = BillCastStay.objects.get_or_create(
            bill=bill, cast_id=cid,
            defaults=dict(
                entered_at=timezone.now(),
                stay_type='free',
            )
        )
        stay.stay_type = 'in' if want_in else 'free'
        stay.left_at   = None          # 常に在席扱い
        stay.save(update_fields=['stay_type', 'left_at'])

        # ② 変更後の inhouse 集合を取得
        new_in = set(
            bill.stays.filter(stay_type='in', left_at__isnull=True)
                .values_list('cast_id', flat=True)
        )

        # ③ 差分に基づき houseNom‑fee 行を同期
        sync_nomination_fees(
            bill,
            prev_main, prev_main,     # 本指名は変化なし
            prev_in,  new_in,
        )

        return Response({'stay_type': stay.stay_type},
                        status=status.HTTP_200_OK)


class BillItemViewSet(viewsets.ModelViewSet):
    queryset = BillItem.objects.all()
    serializer_class = BillItemSerializer

    def get_queryset(self):
        return BillItem.objects.filter(bill_id=self.kwargs["bill_pk"])

    def perform_create(self, serializer):
        serializer.save(bill_id=self.kwargs["bill_pk"])



class CastSalesView(APIView):
    def get(self, request):
        # ----- 月指定が来た場合 -----
        year  = request.query_params.get("year")
        month = request.query_params.get("month")
        if year and month:
            data = get_cast_sales_monthly(int(year), int(month),
                                          store_id=request.query_params.get("store"))
            return Response(data)

        # ----- 日付範囲 (from,to) -----
        today = date.today().isoformat()
        date_from = request.query_params.get("from", today)
        date_to   = request.query_params.get("to",   today)

        data = get_cast_sales(date_from, date_to,
                              store_id=request.query_params.get("store"))
        return Response(data)



class CastViewSet(StoreScopedModelViewSet):
    """
    ・店舗スコープ付き
    ・リスト API では関連を出来るだけ先取りしておく
    ・filterset_fields は元ファイルの両方をマージ
    """
    queryset = (
        Cast.objects
        .select_related('store')
        .prefetch_related('category_rates')
    )
    serializer_class = CastSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = [
        'user__is_active',
        'stage_name',
        'user__username',
    ]


class CastPayoutListView(generics.ListAPIView):
    serializer_class    = CastPayoutDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


    def get_queryset(self):
        qs = (CastPayout.objects
              .select_related('cast',
                              'bill', 'bill__table',
                              'bill_item', 'bill_item__item_master')
              .filter(bill__isnull=False))

        # 店舗スコープ
        if (store := getattr(self.request, 'store', None)):
            qs = qs.filter(bill__table__store=store)

        # キャスト絞り込み
        if (cid := self.request.query_params.get('cast')):
            qs = qs.filter(cast_id=cid)

        # 日付範囲（from / to） YYYY‑MM‑DD
        f = self.request.query_params.get('from')
        t = self.request.query_params.get('to')
        if f and t:
            qs = qs.filter(bill__closed_at__date__range=(f, t))

        return qs.order_by('-bill__closed_at')



class CastItemDetailView(generics.ListAPIView):
    serializer_class   = CastItemDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend]
    filterset_class    = CastItemFilter

    def get_queryset(self):
        cid = self.request.query_params.get('cast')
        f   = self.request.query_params.get('from')
        t   = self.request.query_params.get('to')

        qs = (BillItem.objects
              .select_related('bill', 'bill__table')
              .filter(bill__closed_at__isnull=False))

        # ― 店舗スコープ ―
        if (store := getattr(self.request, 'store', None)):
            qs = qs.filter(bill__table__store=store)

        # ― キャストスコープ (重複しないよう distinct を最後に) ―
        if cid:
            qs = qs.filter(
                Q(served_by_cast_id=cid) |                     # フリー／場内
                Q(is_nomination=True) &                       # 本指名ドリンク
                  (Q(bill__main_cast_id=cid) |                 #   メイン指名
                   Q(bill__nominated_casts__id=cid))           #   追加指名
            )

        # ― 日付スコープ ―
        if f and t:
            qs = qs.filter(bill__closed_at__date__range=(f, t))

        return qs.distinct().order_by('-bill__closed_at')


class ItemCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /item-categories/      一覧
    GET /item-categories/<pk>/ 単件
    （作成・更新・削除は admin から行う想定）
    """
    queryset           = ItemCategory.objects.all()
    serializer_class   = ItemCategorySerializer
    permission_classes = [permissions.IsAuthenticated]




class CastShiftViewSet(StoreScopedModelViewSet):
    queryset = CastShift.objects.select_related('store', 'cast')
    serializer_class = CastShiftSerializer
    filterset_fields = ['cast', 'clock_in', 'clock_out']

    def perform_create(self, serializer):
        sid = self._store(self.request)
        # store がまだ渡っていなければここで注入
        if not serializer.validated_data.get('store'):
            serializer.save(store_id=sid)
        else:
            serializer.save()
            
            
class CastDailySummaryViewSet(StoreScopedModelViewSet):
    """
    GET   /billing/cast-daily-summaries/?from=YYYY-MM-DD&to=YYYY-MM-DD&cast=ID
    """
    serializer_class = CastDailySummarySerializer
    queryset         = CastDailySummary.objects.select_related('cast', 'store')
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['cast', 'work_date']

    # 期間指定 (?from=2025‑07‑01&to=2025‑07‑31)
    def get_queryset(self):
        qs = super().get_queryset()
        f  = self.request.query_params.get('from')
        t  = self.request.query_params.get('to')
        if f and t:
            qs = qs.filter(work_date__range=(f, t))
        return qs.order_by('cast__stage_name', 'work_date')



class CastSalesSummaryView(ListAPIView):
    """
    GET /api/billing/cast-sales/?from=YYYY-MM-DD&to=YYYY-MM-DD
    └ 期間を指定しなければ当月
    """
    serializer_class = CastSalesSummarySerializer      # 下に例あり
    pagination_class = None

    def get_queryset(self):
        f = self.request.query_params.get('from')
        t = self.request.query_params.get('to')
        if not (f and t):
            today = timezone.localdate()
            f = today.replace(day=1)
            t = today

        date_q = Q(daily_summaries__work_date__range=(f, t))

        return (Cast.objects
                # .filter(is_active=True)                # 退店は除外など
                .annotate(
                    sales_champ = Coalesce(Sum(
                        'daily_summaries__sales_champ',  filter=date_q), Value(0)),
                    sales_nom   = Coalesce(Sum(
                        'daily_summaries__sales_nom',    filter=date_q), Value(0)),
                    sales_in    = Coalesce(Sum(
                        'daily_summaries__sales_in',     filter=date_q), Value(0)),
                    sales_free  = Coalesce(Sum(
                        'daily_summaries__sales_free',   filter=date_q), Value(0)),
                    payroll     = Coalesce(Sum(
                        'daily_summaries__payroll',      filter=date_q), Value(0)),
                    total       = F('sales_champ') + F('sales_nom')
                                 + F('sales_in') + F('sales_free'),
                )
                .order_by('stage_name'))


class BillToggleInhouseAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        bill = get_object_or_404(Bill, pk=pk)
        cid  = int(request.data['cast_id'])
        want_in = bool(request.data['inhouse'])


        # ---- ① 変更前の inhouse 集合をキャッシュ
        prev_in = set(
            bill.stays.filter(stay_type='in', left_at__isnull=True)
                .values_list('cast_id', flat=True)
        )
 
        stay, _ = BillCastStay.objects.get_or_create(
            bill=bill, cast_id=cid,
            defaults=dict(
                entered_at=timezone.now(),
                stay_type='in' if want_in else 'free'
            )
        )
        if want_in:
            stay.stay_type = 'in'
            stay.left_at   = None
        else:
            stay.stay_type = 'free'
        stay.save(update_fields=['stay_type', 'left_at'])

        # ---- ② 変更後の inhouse 集合を取得
        new_in = set(
            bill.stays.filter(stay_type='in', left_at__isnull=True)
                .values_list('cast_id', flat=True)
        )
        prev_main = set(bill.nominated_casts.values_list('id', flat=True))
 
        # ---- ③ 差分にもとづき fee 行を同期
        sync_nomination_fees(
            bill,
            prev_main, prev_main,     # main は変化しない
            prev_in,  new_in,
        )
 
        return Response({'stay_type': stay.stay_type})


class CastRankingView(ListAPIView):
    serializer_class = CastRankingSerializer
    pagination_class = None          # 上位 10 名だけ

    def get_queryset(self):
        date_from = self.request.query_params.get('from')
        date_to   = self.request.query_params.get('to')
        if not (date_from and date_to):
            today = timezone.localdate()
            date_from = today.replace(day=1)
            date_to   = today

        # ── Cast モデルから直接集約 ─────────────────
        revenue_expr = (
            F('daily_summaries__sales_free')  +
            F('daily_summaries__sales_in')    +
            F('daily_summaries__sales_nom')   +
            F('daily_summaries__sales_champ')
        )

        return (
            Cast.objects
                .filter(daily_summaries__work_date__range=(date_from, date_to))
                .annotate(revenue=Sum(revenue_expr, output_field=IntegerField()))
                .select_related('store')          # ← avatar は cast.avatar に直接あるので OK
                .order_by('-revenue')[:10]
        )
