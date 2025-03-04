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
    queryset = Reservation.objects.all().order_by("start_time")

    def get_serializer_class(self):
        if self.action == 'create':
            return ReservationCreateSerializer
        return ReservationSerializer


    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_cast_received = instance.cast_received
        old_driver_received = instance.driver_received
        old_store_received = instance.store_received

        store_received = request.data.get("store_received", None)
        driver_received = request.data.get("driver_received", None)
        cast_received = request.data.get("cast_received", None)

        reservation_to_cast_reason = request.data.get("reservation_to_cast_reason", None)
        cast_to_driver_reason = request.data.get("cast_to_driver_reason", None)
        driver_to_store_reason = request.data.get("driver_to_store_reason", None)

        if cast_received is not None:
            instance.cast_received = cast_received

        if driver_received is not None:
            instance.driver_received = driver_received

        if store_received is not None:
            instance.store_received = store_received

        instance.save()

        # 差分の記録
        reservation_to_cast_diff = instance.reservation_amount - instance.cast_received if instance.reservation_amount else None
        cast_to_driver_diff = instance.cast_received - instance.driver_received if instance.cast_received else None
        driver_to_store_diff = instance.driver_received - instance.store_received if instance.store_received else None

        if reservation_to_cast_diff or cast_to_driver_diff or driver_to_store_diff:
            discrepancy = ReservationDiscrepancy.objects.create(
                reservation=instance,
                reservation_to_cast_diff=reservation_to_cast_diff,
                reservation_to_cast_reason=reservation_to_cast_reason,
                cast_to_driver_diff=cast_to_driver_diff,
                cast_to_driver_reason=cast_to_driver_reason,
                driver_to_store_diff=driver_to_store_diff,
                driver_to_store_reason=driver_to_store_reason
            )

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
