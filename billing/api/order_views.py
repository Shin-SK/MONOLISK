# billing/api/order_views.py
from rest_framework.permissions import IsAuthenticated
from billing.permissions import RequireCap, CastHonshimeiForBill

class BillItemCreateView(APIView):
    permission_classes = [IsAuthenticated, RequireCap, CastHonshimeiForBill]
    required_cap = 'cast_order_self'
    # post(self, request, bill_id): bill取得→CastHonshimeiForBillがobjで判定
