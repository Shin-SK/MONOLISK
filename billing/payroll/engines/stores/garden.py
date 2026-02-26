# billing/payroll/engines/stores/garden.py
from django.db.models import Q, Sum, F, IntegerField
from django.db.models.functions import Coalesce
from django.db.models.expressions import ExpressionWrapper

from .. import register
from ..base import BaseEngine
from ....models import (
    BillCastStay,
    BillItem,
    PayrollRunBackRow,
)

# ──────────────────────────────────────────────
# 定数
# ──────────────────────────────────────────────
HOURLY_BY_RANK = {"A": 4000, "B": 3400, "C": 2800, "D": 2000}

# 小計スライドバック閾値テーブル（降順）
_SLIDE_TABLE = [
    (2_000_000, 50),
    (1_700_000, 40),
    (1_600_000, 35),
    (1_500_000, 35),
    (1_400_000, 33),
    (1_300_000, 30),
    (1_200_000, 27),
    (1_100_000, 23),
    (1_000_000, 20),
        (900_000, 12),
        (800_000, 11),
        (700_000, 10),
]


# ──────────────────────────────────────────────
# 純粋関数
# ──────────────────────────────────────────────
def calc_points(sales_total, nom_count, dohan_count):
    """ポイント算出。売上1万円=1pt, 本指名=1pt, 同伴=2pt。"""
    return int(sales_total / 10000) + int(nom_count) + int(dohan_count) * 2


def calc_rank(points):
    points = int(points or 0)
    if points >= 60:
        return "A"
    if points >= 30:
        return "B"
    if points >= 1:
        return "C"
    return "D"


def calc_slide_rate(sales_total):
    """小計スライドバックの率(%)を返す。70万未満は0。"""
    sales_total = int(sales_total or 0)
    for threshold, rate in _SLIDE_TABLE:
        if sales_total >= threshold:
            return rate
    return 0


def calc_monthly_back(rank, sales_total, dohan_sales_total):
    """
    月次バック各項目を dict で返す。
    keys: slide_back, dohan_back, b_back
    """
    result = {"slide_back": 0, "dohan_back": 0, "b_back": 0}

    sales_total = int(sales_total or 0)
    dohan_sales_total = int(dohan_sales_total or 0)

    # 小計スライドバック（Aのみ）
    if rank == "A":
        rate = calc_slide_rate(sales_total)
        if rate:
            result["slide_back"] = int(sales_total * rate / 100)

    # 同伴バック（A のみ）
    if rank == "A" and dohan_sales_total >= 700_000:
        result["dohan_back"] = int(dohan_sales_total * 10 / 100)

    # B ランク専用バック
    if rank == "B":
        result["b_back"] = int(sales_total * 5 / 100)

    return result


# ──────────────────────────────────────────────
# 集計クエリ
# ──────────────────────────────────────────────
def calculate_garden_stats(store, cast_id, period_start, period_end):
    """
    Garden 月次制度の集計を行い dict を返す。
    bill.closed_at__date が period 内のものを対象。
    """
    item_subtotal_expr = ExpressionWrapper(F("price") * F("qty"), output_field=IntegerField())

    bill_item_filter = Q(
        bill__table__store=store,
        bill__closed_at__date__range=(period_start, period_end),
        served_by_cast_id=cast_id,
    )

    # sales_total: served_by_cast ベース（price*qty）
    sales_total = (
        BillItem.objects.filter(bill_item_filter)
        .aggregate(total=Coalesce(Sum(item_subtotal_expr), 0))
        .get("total")
    ) or 0

    # dohan bill ids (QuerySet)
    dohan_bill_ids_qs = (
        BillCastStay.objects.filter(
            bill__table__store=store,
            bill__closed_at__date__range=(period_start, period_end),
            stay_type="dohan",
            cast_id=cast_id,
        )
        .values_list("bill_id", flat=True)
        .distinct()
    )

    # dohan_count: 伝票単位
    dohan_count = dohan_bill_ids_qs.count()

    # dohan_sales_total: 同伴伝票の served_by_cast ベース小計
    dohan_sales_total = (
        BillItem.objects.filter(
            bill_id__in=dohan_bill_ids_qs,
            served_by_cast_id=cast_id,
        )
        .aggregate(total=Coalesce(Sum(item_subtotal_expr), 0))
        .get("total")
    ) or 0

    # nom_count: 伝票単位（本指名）
    nom_count = (
        BillCastStay.objects.filter(
            bill__table__store=store,
            bill__closed_at__date__range=(period_start, period_end),
            stay_type="nom",
            cast_id=cast_id,
        ).values("bill_id").distinct().count()
    )

    points = calc_points(sales_total, nom_count, dohan_count)
    rank = calc_rank(points)
    backs = calc_monthly_back(rank, sales_total, dohan_sales_total)

    return {
        "sales_total": sales_total,
        "dohan_sales_total": dohan_sales_total,
        "nom_count": nom_count,
        "dohan_count": dohan_count,
        "points": points,
        "rank": rank,
        "hourly": HOURLY_BY_RANK[rank],
        "slide_rate": calc_slide_rate(sales_total) if rank == "A" else 0,
        **backs,
    }


# ──────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────
@register("garden")
class GardenEngine(BaseEngine):

    def finalize_payroll_line(self, line, period_start, period_end):
        stats = calculate_garden_stats(
            self.store, line.cast_id, period_start, period_end,
        )

        # 時給再計算: worked_min * hourly / 60
        new_hourly_pay = int((int(line.worked_min or 0) * int(stats["hourly"] or 0)) / 60)
        monthly_back = stats["slide_back"] + stats["dohan_back"] + stats["b_back"]

        line.hourly_pay = new_hourly_pay
        line.commission = int(line.commission or 0) + int(monthly_back or 0)
        line.total = line.hourly_pay + line.commission
        line.garden_snapshot = {
            "rank": stats["rank"],
            "points": stats["points"],
            "sales_total": stats["sales_total"],
            "dohan_sales_total": stats["dohan_sales_total"],
            "nom_count": stats["nom_count"],
            "dohan_count": stats["dohan_count"],
            "hourly": stats["hourly"],
            "slide_rate": stats["slide_rate"],
            "slide_back": stats["slide_back"],
            "dohan_back": stats["dohan_back"],
            "b_back": stats["b_back"],
            "monthly_back": monthly_back,
        }

        # 追加の BackRow
        extra_rows = []
        run = line.run

        if stats["slide_back"]:
            extra_rows.append(PayrollRunBackRow(
                run=run, cast=line.cast,
                label="GDN_SLIDE", amount=stats["slide_back"],
            ))
        if stats["dohan_back"]:
            extra_rows.append(PayrollRunBackRow(
                run=run, cast=line.cast,
                label="GDN_DOHAN", amount=stats["dohan_back"],
            ))
        if stats["b_back"]:
            extra_rows.append(PayrollRunBackRow(
                run=run, cast=line.cast,
                label="GDN_SUBTOTAL_5", amount=stats["b_back"],
            ))

        return extra_rows
