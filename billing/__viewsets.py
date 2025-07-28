# billing/viewsets.py
from django.conf	  import settings
from django.apps	  import apps
from rest_framework	import viewsets, generics, permissions
from django.db.models import Sum, F, Q
from django_filters.rest_framework import DjangoFilterBackend

from .models import Cast, CastPayout ,BillItem, ItemCategory
from .serializers import CastSalesSummarySerializer, CastPayoutDetailSerializer, CastItemDetailSerializer, CastSerializer, ItemCategorySerializer
from .filters import CastPayoutFilter, CastItemFilter

from django.db.models.functions import Coalesce
from datetime import date

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


class CastViewSet(viewsets.ModelViewSet):
    queryset           = Cast.objects.select_related('store').prefetch_related('category_rates')
    serializer_class   = CastSerializer
    permission_classes = [permissions.IsAuthenticated]


class CastPayoutListView(generics.ListAPIView):
	serializer_class  = CastPayoutDetailSerializer
	permission_classes = [permissions.IsAuthenticated]
	filter_backends = [DjangoFilterBackend]
	filterset_class = CastPayoutFilter

	def get_queryset(self):
		store = getattr(self.request, 'store', None)
		qs = (CastPayout.objects
			.select_related('bill')
			  .filter(bill__isnull=False))
		if store:
			qs = qs.filter(bill__table__store=store)
		return qs.order_by('-bill__closed_at')


class CastItemDetailView(generics.ListAPIView):
	serializer_class  = CastItemDetailSerializer
	permission_classes = [permissions.IsAuthenticated]
	filter_backends	= [DjangoFilterBackend]
	filterset_class	= CastItemFilter

	def get_queryset(self):
		store = getattr(self.request, 'store', None)
		qs = (BillItem.objects
			  .select_related('bill', 'bill__table')
			  .filter(bill__closed_at__isnull=False,
					  served_by_cast__isnull=False))
		if store:
			qs = qs.filter(bill__table__store=store)
		return qs.order_by('-bill__closed_at')


class ItemCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /item-categories/      一覧
    GET /item-categories/<pk>/ 単件
    （作成・更新・削除は admin から行う想定）
    """
    queryset           = ItemCategory.objects.all()
    serializer_class   = ItemCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

