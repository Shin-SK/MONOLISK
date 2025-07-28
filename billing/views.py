#billing/views.py

from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .services import get_cast_sales 
from django.conf	  import settings
from django.apps	  import apps
from rest_framework	import viewsets, generics, permissions
from django.db.models import Sum, F, Q
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models.functions import Coalesce
from datetime import date

from .models import Store, Table, Bill, ItemMaster, BillItem, CastPayout, Cast, BillCastStay, Cast, CastPayout ,BillItem, ItemCategory
from .serializers import CastSalesSummarySerializer, CastPayoutDetailSerializer, CastItemDetailSerializer, CastSerializer, ItemCategorySerializer, 	StoreSerializer, TableSerializer, BillSerializer, ItemMasterSerializer, BillItemSerializer, CastSerializer
from .filters import CastPayoutFilter, CastItemFilter


StoreModel = apps.get_model(settings.STORE_MODEL)	# billing.Store を取得

class StoreScopedModelViewSet(viewsets.ModelViewSet):
	def _store_id(self):
		return getattr(self.request.user, 'store_id', None) \
			or settings.DEFAULT_STORE_ID

	def get_queryset(self):
		qs  = super().get_queryset()
		sid = self._store_id()

		# 対象が Store 自体
		if qs.model is StoreModel:
			return qs.filter(pk=sid)

		# 他モデルなら store_id を持つ場合だけフィルタ
		if 'store_id' in (f.name for f in qs.model._meta.fields):
			return qs.filter(store_id=sid)
		return qs


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


class ItemMasterViewSet(StoreScopedModelViewSet):
	queryset = ItemMaster.objects.all()
	serializer_class = ItemMasterSerializer

class TableViewSet(StoreScopedModelViewSet):
	queryset = Table.objects.all()
	serializer_class = TableSerializer

class CastViewSet(StoreScopedModelViewSet):
	queryset = Cast.objects.all()
	serializer_class = CastSerializer
	filterset_fields = ['user__is_active', 'stage_name', 'user__username']


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
		"""
		bill	= self.get_object()
		cid	 = int(request.data.get('cast_id'))
		make_in = bool(request.data.get('inhouse'))

		stay, _ = BillCastStay.objects.get_or_create(
			bill=bill, cast_id=cid,
			defaults=dict(
				entered_at=timezone.now(),
				stay_type='free',
			)
		)

		stay.stay_type = 'in' if make_in else 'free'
		stay.left_at   = None		  # 在席扱い
		stay.save(update_fields=['stay_type', 'left_at'])

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




class CastViewSet(viewsets.ModelViewSet):
	queryset		   = Cast.objects.select_related('store').prefetch_related('category_rates')
	serializer_class   = CastSerializer
	permission_classes = [permissions.IsAuthenticated]


class CastPayoutListView(generics.ListAPIView):
	serializer_class	= CastPayoutDetailSerializer
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


# class CastItemDetailView(generics.ListAPIView):
# 	serializer_class  = CastItemDetailSerializer
# 	permission_classes = [permissions.IsAuthenticated]
# 	filter_backends	= [DjangoFilterBackend]
# 	filterset_class	= CastItemFilter          # ← 使わないなら削除しても可

# 	def get_queryset(self):
# 		qs = (BillItem.objects
# 			  .select_related('bill', 'bill__table')
# 			  .filter(bill__closed_at__isnull=False,
# 					  served_by_cast__isnull=False))

# 		# ─ 店舗スコープ ─
# 		if (store := getattr(self.request, 'store', None)):
# 			qs = qs.filter(bill__table__store=store)

# 		# ─ キャスト絞り込み (?cast=ID) ─
# 		if (cid := self.request.query_params.get('cast')):
# 			qs = qs.filter(served_by_cast_id=cid)

# 		# ─ 日付範囲 (?from=YYYY-MM-DD&to=YYYY-MM-DD) ─
# 		f = self.request.query_params.get('from')
# 		t = self.request.query_params.get('to')
# 		if f and t:
# 			qs = qs.filter(bill__closed_at__date__range=(f, t))

# 		return qs.order_by('-bill__closed_at')

class CastItemDetailView(generics.ListAPIView):
    serializer_class   = CastItemDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends	= [DjangoFilterBackend]
    filterset_class	= CastItemFilter

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
	GET /item-categories/	  一覧
	GET /item-categories/<pk>/ 単件
	（作成・更新・削除は admin から行う想定）
	"""
	queryset		   = ItemCategory.objects.all()
	serializer_class   = ItemCategorySerializer
	permission_classes = [permissions.IsAuthenticated]

