# api/pl_views.py
from __future__ import annotations

from django.conf import settings
from datetime import date, timedelta
from typing    import Any, Dict, List

from rest_framework.views       import APIView
from rest_framework.response    import Response
from rest_framework             import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated

from billing.utils.pl_daily   import get_daily_pl
from billing.utils.pl_monthly import get_monthly_pl
from billing.utils.pl_yearly  import get_yearly_pl

from billing.permissions import RequireCap, OwnerReadOnly

# ───────────────────────────────
# 入力シリアライザ
# ───────────────────────────────
class _DailyReq(serializers.Serializer):
    date     = serializers.DateField()
    store_id = serializers.IntegerField(required=False, allow_null=True)

class _MonthlyReq(serializers.Serializer):
    year     = serializers.IntegerField(min_value=2000, max_value=2100)
    month    = serializers.IntegerField(min_value=1, max_value=12)
    store_id = serializers.IntegerField(required=False, allow_null=True)

class _YearlyReq(serializers.Serializer):
    year     = serializers.IntegerField(min_value=2000, max_value=2100)
    store_id = serializers.IntegerField(required=False, allow_null=True)

# ───────────────────────────────
# 共通ヘルパ
# ───────────────────────────────
def _resolve_store(request, raw) -> int | None:
    """
    store_id 補完ロジック
      1) 明示的な store_id
      2) request.store            (ミドルウェア等で付与されている場合)
      3) request.user.store_id
    """
    if raw not in (None, ""):
        return int(raw)

    if getattr(request, "store", None):
        return request.store.id

    if request.user.store_id:
        return request.user.store_id

    return None

# フロント互換のダミー列をマージする
def _add_front_stubs(rec: Dict[str, Any]) -> Dict[str, Any]:
    # 既存値は尊重。無いキーだけデフォルトを補う
    if "sales_cash" not in rec:
        rec["sales_cash"] = 0
    if "sales_card" not in rec:
        rec["sales_card"] = 0
    rec.setdefault("cast_labor",   rec.get("labor_cost", 0))
    rec.setdefault("driver_labor", 0)
    rec.setdefault("custom_expense", 0)
    rec.setdefault("gross_profit", rec.get("operating_profit", 0))
    return rec

# ───────────────────────────────
# 日次 P/L
# ───────────────────────────────
class DailyPLAPIView(APIView):
    """
    GET /api/billing/pl/daily/?date=2025-08-01&store_id=1
    """
    permission_classes = [AllowAny]

    def get(self, request):
        ser = _DailyReq(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        store_id = _resolve_store(request, data.get("store_id"))
        if store_id is None:
            return Response({"detail": "store_id を指定してください"}, status=400)

        dpl = get_daily_pl(data["date"], store_id=store_id)
        return Response(_add_front_stubs(dpl))

# ───────────────────────────────
# 月次 P/L
# ───────────────────────────────
class MonthlyPLAPIView(APIView):
    """
    GET /api/billing/pl/monthly/?year=2025&month=8&store_id=1
    """
    permission_classes = [AllowAny]

    def get(self, request):
        ser = _MonthlyReq(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        store_id = _resolve_store(request, data.get("store_id"))
        if store_id is None:
            return Response({"detail": "store_id を指定してください"}, status=400)

        # ---- 日次一覧を作る -----------------------------
        first = date(data["year"], data["month"], 1)
        last  = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

        days: List[Dict[str, Any]] = []
        cur = first
        while cur <= last:
            dpl = get_daily_pl(cur, store_id=store_id)
            days.append(_add_front_stubs(dpl))
            cur += timedelta(days=1)

        # ---- 月次合計 ----------------------------------
        mpl = get_monthly_pl(data["year"], data["month"], store_id=store_id)
        monthly_total = _add_front_stubs(mpl)

        return Response({"days": days, "monthly_total": monthly_total})

# ───────────────────────────────
# 年次 P/L
# ───────────────────────────────
class YearlyPLAPIView(APIView):
    """
    GET /api/billing/pl/yearly/?year=2025&store_id=1
    """
    permission_classes = [AllowAny]

    def get(self, request):
        ser = _YearlyReq(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        store_id = _resolve_store(request, data.get("store_id"))
        if store_id is None:
            return Response({"detail": "store_id を指定してください"}, status=400)

        ypl = get_yearly_pl(data["year"], store_id=store_id)

        # totals と months[*].totals にだけダミー埋め
        ypl["totals"] = _add_front_stubs(ypl.get("totals", {}))
        for m in ypl.get("months", []):
            m["totals"] = _add_front_stubs(m.get("totals", {}))

        return Response(ypl)


class StorePLView(APIView):
    permission_classes = [IsAuthenticated, RequireCap]
    required_cap = 'view_pl_store'
    # get() 実装は既存のまま

class OwnerPLSummaryView(APIView):
    permission_classes = [IsAuthenticated, RequireCap, OwnerReadOnly]
    required_cap = 'view_pl_multi'
    # get() 実装：store_ids[]=... を受けて横断集計