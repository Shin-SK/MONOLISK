from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from reservation.models import Reservation

class ReservationSalesAPIView(APIView):
    def get(self, request):
        # クエリパラメータの取得
        store = request.query_params.get('store', None)
        cast = request.query_params.get('cast', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)

        # 予約データをフィルタリング
        query = Reservation.objects.all()

        # 動的フィルタリング
        if store:
            query = query.filter(store_id=store)
        if cast:
            query = query.filter(cast_id=cast)
        if start_date and end_date:
            query = query.filter(start_time__gte=start_date, start_time__lte=end_date)

        # 予約の詳細データを返す（フィルタリングされた予約）
        reservations = query.values(
            'id', 'customer_name', 'start_time', 'course__name', 'store__name', 
            'cast__full_name', 'driver__full_name', 'cast_received', 'driver_received', 'store_received'
        )

        # 売上合計を集計
        total_sales = query.aggregate(
            total_cast_received=Sum('cast_received'),
            total_driver_received=Sum('driver_received'),
            total_store_received=Sum('store_received')
        )

        # 日別売上の集計（動的フィルタリングに基づく）
        daily_sales = query.values('start_time__date').annotate(
            total_cast_received=Sum('cast_received'),
            total_driver_received=Sum('driver_received'),
            total_store_received=Sum('store_received')
        ).order_by('start_time__date')

        return Response({
            'total_sales': total_sales,
            'daily_sales': daily_sales,
            'reservations': reservations
        })
