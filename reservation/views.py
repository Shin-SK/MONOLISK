from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Reservation, Course, Menu, Discount
from .serializers import (
    ReservationSerializer,
    ReservationCreateSerializer,
    CourseSerializer,
    MenuSerializer,
    DiscountSerializer
)
from account.models import CustomUser, Store

class ReservationViewSet(viewsets.ModelViewSet):
    """
    /api/reservations/ に対するCRUD
    """
    queryset = Reservation.objects.all().order_by("start_time")

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ReservationCreateSerializer
        return ReservationSerializer

def update(self, request, *args, **kwargs):
    """
    フロントから送られる cast_received / driver_received / store_received を
    そのまま更新するだけ。
    差分や理由の記録は行わない。
    """
    instance = self.get_object()

    # 1. リクエストから数値を取得
    store_received = request.data.get("store_received", None)
    driver_received = request.data.get("driver_received", None)
    cast_received = request.data.get("cast_received", None)

    # 2. あれば上書き
    if cast_received is not None:
        instance.cast_received = cast_received
    if driver_received is not None:
        instance.driver_received = driver_received
    if store_received is not None:
        instance.store_received = store_received

    # 3. 保存
    instance.save()

    # 4. 更新結果を返す
    serializer = self.get_serializer(instance)
    return Response(serializer.data, status=status.HTTP_200_OK)



class UnpaidRoutesAPIView(APIView):
    """
    指定されたドライバーの未入金の予約一覧を取得
    """
    def get(self, request, driver_id):
        unpaid_reservations = Reservation.objects.filter(
            driver_id=driver_id,
            store_received__isnull=True
        )
        serializer = ReservationSerializer(unpaid_reservations, many=True)
        return Response({'unpaid_reservations': serializer.data})


class CourseListAPIView(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


class MenuListAPIView(generics.ListAPIView):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer


class DiscountListAPIView(generics.ListAPIView):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
