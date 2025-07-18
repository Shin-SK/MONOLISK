from .viewsets import StoreScopedModelViewSet

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from .models import Store, Table, Bill, ItemMaster, BillItem, CastPayout, Cast
from .serializers import (
	StoreSerializer, TableSerializer, BillSerializer,
	ItemMasterSerializer, BillItemSerializer,CastSerializer
)


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
		Bill.objects
			.select_related('table__store')
			.prefetch_related('items', 'stays', 'nominated_casts', 'inhouse_casts')
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
		"""
		締め処理：サービス料・税・キャストバック計算
		"""
		session = self.get_object()
		if session.closed_at:
			return Response({'detail': 'already closed'}, status=400)

		with transaction.atomic():
			session.closed_at = timezone.now()
			session.save()

			# ── 小計 & back を計算
			sub_total = sum(i.subtotal for i in session.items.all())
			back_rate = request.data.get('back_rate', 0)	# フォールバック

			nominated = list(session.nominated_casts.all())
			if nominated:
				base_back = sub_total * back_rate
				per_cast	= int(base_back / len(nominated))
				for cast in nominated:
					CastPayout.objects.create(
						bill_item = None,
						cast	  = cast,
						amount	  = per_cast
					)

		return Response({'detail': 'closed'}, status=status.HTTP_200_OK)


class BillItemViewSet(viewsets.ModelViewSet):
	queryset = BillItem.objects.all()
	serializer_class = BillItemSerializer

	def get_queryset(self):
		return BillItem.objects.filter(bill_id=self.kwargs["bill_pk"])

	def perform_create(self, serializer):
		serializer.save(bill_id=self.kwargs["bill_pk"])

