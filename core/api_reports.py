# core/api_reports.py などに
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone
from .models import ExpenseEntry, ShiftPlan, ShiftAttendance, CastRate, DriverRate

class ProfitLoss(APIView):
    """
    /api/pl/?scope=daily&date=2025-07-03
    /api/pl/?scope=monthly&month=2025-07
    store パラメータ任意 (?store=<id>)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        scope = request.GET.get('scope', 'monthly')
        store = request.GET.get('store')

        # ====== 期間の決定 ======
        if scope == 'daily':
            target = request.GET.get('date') or timezone.localdate()
            date_from = date_to = target
        else:  # monthly
            month = request.GET.get('month') or timezone.localdate().strftime('%Y-%m')
            y, m = map(int, month.split('-'))
            date_from = timezone.datetime(y, m, 1).date()
            # 月末日を求める小技
            next_month = (timezone.datetime(y, m, 28) + timezone.timedelta(days=4)).date()
            date_to = (next_month.replace(day=1) - timezone.timedelta(days=1))

        # ====== 売上集計 ======
        sales_qs = Reservation.objects.filter(start_at__date__range=(date_from, date_to))
        if store: sales_qs = sales_qs.filter(store_id=store)
        total_sales = sales_qs.aggregate(s=Sum('received_amount'))['s'] or 0

        # ====== 経費集計 ======
        exp_qs = ExpenseEntry.objects.filter(date__range=(date_from, date_to))
        if store: exp_qs = exp_qs.filter(
            models.Q(store_id=store) | models.Q(store__isnull=True)
        )
        exp_total = exp_qs.aggregate(s=Sum('amount'))['s'] or 0

        # ====== 人件費サンプル（キャスト） ======
        # ※ 実運用では ShiftAttendance 使って実働分を計算
        cast_labor = 0  # ← ざっくり 0 で返す例

        return Response({
            'scope': scope,
            'from':  date_from,
            'to':    date_to,
            'sales': total_sales,
            'expenses': exp_total,
            'labor_cast': cast_labor,
            'gross_profit': total_sales - (exp_total + cast_labor),
        })
