# billing/api/pl_views.py
from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers

from billing.utils.pl_daily import get_daily_pl
from billing.utils.pl_monthly import get_monthly_pl
from billing.utils.pl_yearly import get_yearly_pl


from rest_framework.permissions import AllowAny

# ────────── シリアライザ ────────────────────────────
class DailyPLRequestSerializer(serializers.Serializer):
    date      = serializers.DateField()
    store_id  = serializers.IntegerField(required=False, allow_null=True)

class MonthlyPLRequestSerializer(serializers.Serializer):
    year      = serializers.IntegerField(min_value=2000, max_value=2100)
    month     = serializers.IntegerField(min_value=1, max_value=12)
    store_id  = serializers.IntegerField(required=False, allow_null=True)

# ────────── ビュー ──────────────────────────────────
class DailyPLAPIView(APIView):
    """
    GET /api/pl/daily/?date=2025-07-17&store_id=1
    """
    permission_classes = [AllowAny]

    def get(self, request):
        ser = DailyPLRequestSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        pl   = get_daily_pl(
            data["date"],
            store_id=data.get("store_id"),
        )
        return Response(pl)


class MonthlyPLAPIView(APIView):
    """
    GET /api/billing/pl/monthly/?year=2025&month=7&store_id=1
    """
    permission_classes = [AllowAny]        # ← 401 回避用

    def get(self, request):
        ser = MonthlyPLRequestSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        pl = get_monthly_pl(
            data["year"], data["month"],
            store_id=data.get("store_id"),
        )
        return Response(pl)



class YearlyPLRequestSerializer(serializers.Serializer):
    year     = serializers.IntegerField(min_value=2000, max_value=2100)
    store_id = serializers.IntegerField(required=False, allow_null=True)

class YearlyPLAPIView(APIView):
    """
    GET /api/billing/pl/yearly/?year=2025&store_id=1
    """
    permission_classes = [AllowAny]

    def get(self, request):
        ser = YearlyPLRequestSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        pl = get_yearly_pl(
            data["year"],
            store_id=data.get("store_id"),
        )
        return Response(pl)