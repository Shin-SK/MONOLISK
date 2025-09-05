# billing/kds_views.py（丸ごと置き換え）
import time
from django.utils import timezone
from django.db.models import Exists, OuterRef
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework import permissions
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from billing.permissions import RequireCap

from .models import OrderTicket, Staff, Store, StaffShift
from .serializers import (
    OrderTicketSerializer,
    OrderTicketHistorySerializer,
    StaffMiniSerializer,
)

ALLOWED_ROUTES = {'kitchen', 'drinker'}

def _require_store_id(request):
    # 1) ユーザー紐付け or middleware
    sid = getattr(request.user, 'store_id', None)
    if not sid and getattr(request, 'store', None):
        sid = request.store.id
    # 2) superuser は明示指定を許可
    if not sid and request.user.is_superuser:
        raw = request.headers.get('X-Store-Id') or request.query_params.get('store_id')
        try:
            sid = int(raw) if raw else None
        except (TypeError, ValueError):
            sid = None
        if sid and not Store.objects.filter(pk=sid).exists():
            sid = None
    return sid


# ---------- station: NEW/ACK 一覧 ----------
class KDSTicketList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        route = request.query_params.get('route')
        if route not in ALLOWED_ROUTES:
            return Response({'detail': 'route 必須: kitchen|drinker'}, status=400)

        sid = _require_store_id(request)
        if not sid:
            return Response({'detail': 'store コンテキストが必要です'}, status=400)

        qs = (OrderTicket.objects
              .select_related('bill_item', 'bill_item__bill', 'bill_item__bill__table')
              .filter(store_id=sid, route=route,
                      state__in=[OrderTicket.STATE_NEW, OrderTicket.STATE_ACK])
              .order_by('created_at'))
        return Response(OrderTicketSerializer(qs, many=True).data)


class KDSTicketAck(APIView):
    permission_classes = [IsAuthenticated, RequireCap]
    required_cap = 'station_operate'

    def post(self, request, pk: int):
        sid = _require_store_id(request)
        obj = get_object_or_404(OrderTicket, pk=pk, store_id=sid)
        obj.mark_ack()
        obj.save(update_fields=['state', 'acked_at'])
        return Response({'ok': True})


class KDSTicketReady(APIView):
    permission_classes = [IsAuthenticated, RequireCap]
    required_cap = 'station_operate'

    def post(self, request, pk: int):
        sid = _require_store_id(request)
        obj = get_object_or_404(OrderTicket, pk=pk, store_id=sid)
        obj.mark_ready()
        obj.save(update_fields=['state', 'ready_at'])
        return Response({'ok': True})


# ---------- station: NEW/ACK long-poll（IDカーソル） ----------
class KDSTicketLongPoll(APIView):
    """
    GET /api/billing/kds/longpoll-tickets?route=drinker&since_id=0
    """
    permission_classes = [IsAuthenticated, RequireCap]
    required_cap = 'station_view'

    def get(self, request):
        route = request.query_params.get('route')
        if route not in ALLOWED_ROUTES:
            return Response({'detail': 'route 必須: kitchen|drinker'}, status=400)

        sid = _require_store_id(request)
        if not sid:
            return Response({'detail': 'store コンテキストが必要です'}, status=400)

        try:
            since_id = int(request.query_params.get('since_id', 0) or 0)
        except ValueError:
            since_id = 0

        deadline = time.time() + 25
        while time.time() < deadline:
            qs = (OrderTicket.objects
                  .select_related('bill_item','bill_item__bill','bill_item__bill__table')
                  .filter(store_id=sid, route=route,
                          state__in=[OrderTicket.STATE_NEW, OrderTicket.STATE_ACK],
                          pk__gt=since_id)
                  .order_by('pk'))
            if qs.exists():
                data = OrderTicketSerializer(qs, many=True).data
                cursor = max(x['id'] for x in data)
                return Response({'tickets': data, 'cursor': cursor})
            time.sleep(1)

        return Response({'tickets': [], 'cursor': since_id, 'timeout': True})


# ---------- deshap: READY 一覧 / 持ってく ----------
class KDSReadyList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sid = _require_store_id(request)
        if not sid:
            return Response({'detail': 'store コンテキストが必要です'}, status=400)

        qs = (OrderTicket.objects
              .select_related('bill_item', 'bill_item__bill', 'bill_item__bill__table')
              .filter(store_id=sid, state=OrderTicket.STATE_READY, archived_at__isnull=True)
              .order_by('created_at'))
        return Response(OrderTicketSerializer(qs, many=True).data)


class KDSTakeTicket(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        sid = _require_store_id(request)
        if not sid:
            return Response({'detail': 'store コンテキストが必要です'}, status=400)

        ticket_id = request.data.get('ticket_id')
        staff_id  = request.data.get('staff_id')
        if not ticket_id or not staff_id:
            return Response({'detail': 'ticket_id と staff_id が必要です'}, status=400)

        ticket = get_object_or_404(OrderTicket, pk=ticket_id, store_id=sid,
                                   state=OrderTicket.STATE_READY, archived_at__isnull=True)
        staff  = get_object_or_404(Staff, pk=staff_id)
        if not staff.stores.filter(pk=sid).exists():
            return Response({'detail': 'この店舗のスタッフではありません'}, status=403)

        ticket.archive_by(staff)
        ticket.save(update_fields=['taken_by_staff', 'taken_at', 'archived_at'])
        return Response({'ok': True})


# ---------- deshap: READY long-poll（IDカーソル） ----------
class KDSReadyLongPoll(APIView):
    """
    GET /api/billing/kds/longpoll-ready?since_id=0
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sid = _require_store_id(request)
        if not sid:
            return Response({'detail': 'store コンテキストが必要です'}, status=400)

        try:
            since_id = int(request.query_params.get('since_id', 0) or 0)
        except ValueError:
            since_id = 0

        deadline = time.time() + 25
        while time.time() < deadline:
            qs = (OrderTicket.objects
                  .select_related('bill_item','bill_item__bill','bill_item__bill__table')
                  .filter(store_id=sid,
                          state=OrderTicket.STATE_READY,
                          archived_at__isnull=True,
                          pk__gt=since_id)
                  .order_by('pk'))
            if qs.exists():
                data = OrderTicketSerializer(qs, many=True).data
                cursor = max(x['id'] for x in data)
                return Response({'ready': data, 'cursor': cursor})
            time.sleep(1)

        return Response({'ready': [], 'cursor': since_id, 'timeout': True})


# ---------- deshap: 今日の履歴 ----------
class KDSTakenTodayList(APIView):
    """
    GET /api/billing/kds/taken-today/?limit=50
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sid = _require_store_id(request)
        if not sid:
            return Response({'detail': 'store コンテキストが必要です'}, status=400)

        try:
            limit = int(request.query_params.get('limit', 50))
        except ValueError:
            limit = 50

        today = timezone.localdate()
        qs = (OrderTicket.objects
              .select_related('bill_item', 'bill_item__bill', 'bill_item__bill__table',
                              'taken_by_staff', 'taken_by_staff__user')
              .filter(store_id=sid, archived_at__isnull=False, archived_at__date=today)
              .order_by('-archived_at')[:limit])
        return Response(OrderTicketHistorySerializer(qs, many=True).data)


# ---------- staffs: 出勤中一覧 ----------
class StaffList(ListAPIView):
    """
    GET /api/billing/staffs/?active=1  # 出勤中のみ
    GET /api/billing/staffs/           # 所属全員
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = StaffMiniSerializer

    def get_queryset(self):
        sid = _require_store_id(self.request)
        qs  = Staff.objects.select_related('user')

        active = str(self.request.query_params.get('active', '')).lower()
        if active in ('1', 'true', 'yes'):
            active_q = StaffShift.objects.filter(
                staff=OuterRef('pk'),
                store_id=sid,
                clock_in__isnull=False,
                clock_out__isnull=True,
            )
            qs = qs.annotate(is_active=Exists(active_q)).filter(is_active=True)
        else:
            qs = qs.filter(stores__id=sid).distinct()

        return qs.order_by('user__username')


