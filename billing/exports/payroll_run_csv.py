# billing/exports/payroll_run_csv.py
import csv
import io
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from django.db.models import OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from ..models import (
    Store,
    Cast,
    CastDailySummary,
    CastPayout,
    PayrollRun,
    PayrollRunLine,
    PayrollRunBackRow,
)
from ..permissions import RequireCap


# exp.csv に合わせた 17列
CSV_COLUMNS = [
    "名前",
    "時給合計",
    "バック合計",
    "給与合計",
    "区分",
    "出勤",
    "退勤",
    "勤務時間(h)",
    "時給",
    "時給給与",
    "伝票ID",
    "注文ID",
    "品目",
    "単価",
    "個数",
    "小計",
    "バック",
]


def _get_store_id_from_header(request):
    """Store-Locked: ヘッダーから店舗IDを取得"""
    sid = request.META.get("HTTP_X_STORE_ID")
    if not sid:
        raise ValueError("X-Store-Id header is required")
    return int(sid)


def _get_default_payroll_period(store, today=None):
    """
    views.py にあった get_default_payroll_period 相当（循環import回避用）
    """
    if today is None:
        today = date.today()

    if store.payroll_cutoff_kind == Store.PAYROLL_CUTOFF_EOM:
        # 月末締め
        if today.day == 1:
            period_end = today - relativedelta(days=1)
        else:
            period_end = (today.replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)
        period_start = period_end.replace(day=1)
        return (period_start, period_end)

    # 日付締め（例: 25締め）
    cutoff_day = store.payroll_cutoff_day or 25

    if today.day < cutoff_day:
        period_end = today.replace(day=cutoff_day) - relativedelta(months=1)
        period_start = period_end - relativedelta(months=1)
        period_start = period_start.replace(day=cutoff_day) + relativedelta(days=1)
    else:
        period_end = today.replace(day=cutoff_day)
        period_start = period_end - relativedelta(months=1)
        period_start = period_start.replace(day=cutoff_day) + relativedelta(days=1)

    return (period_start, period_end)


def _check_overlap(store, period_start, period_end):
    """既存の PayrollRun と重複があれば True を返す"""
    overlap_qs = PayrollRun.objects.filter(
        store=store,
        period_start__lte=period_end,
        period_end__gte=period_start,
    )
    return overlap_qs.exists()


def _round_hours(worked_min: int) -> float:
    return round((int(worked_min or 0) / 60.0), 2)


def _fmt_dt(val):
    """
    出勤/退勤用: datetime -> 'YYYY/MM/DD HH:MM'
    date -> 'YYYY/MM/DD'
    None -> ''
    """
    if not val:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y/%m/%d %H:%M")
    if isinstance(val, date):
        return val.strftime("%Y/%m/%d")
    # 文字列などが入ってても落ちないように
    return str(val)


def _safe_int(v, default=0):
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default


def _row(writer, values):
    """
    常に 17 列に揃えて書き出す
    """
    vals = list(values)
    if len(vals) < len(CSV_COLUMNS):
        vals += [""] * (len(CSV_COLUMNS) - len(vals))
    writer.writerow(vals[: len(CSV_COLUMNS)])


class PayrollRunExportCSVView(APIView):
    """
    POST /api/billing/payroll/runs/export.csv

    権限: user_manage (Manager専用)

    リクエストボディ:
    {
      "from": "YYYY-MM-DD",  // 省略可（省略時はデフォルト期間）
      "to": "YYYY-MM-DD",    // 省略可
      "note": "任意メモ"     // 省略可
    }

    レスポンス: CSV（UTF-8 BOM付き）
    """
    permission_classes = [IsAuthenticated, RequireCap]
    required_cap = "user_manage"

    def post(self, request):
        sid = _get_store_id_from_header(request)
        store = get_object_or_404(Store, pk=sid)

        from_param = request.data.get("from")
        to_param = request.data.get("to")
        note = request.data.get("note", "")

        if from_param and to_param:
            df = date.fromisoformat(from_param)
            dt = date.fromisoformat(to_param)
        else:
            df, dt = _get_default_payroll_period(store, date.today())

        # 重複警告（CSV出力は続行）
        overlap = _check_overlap(store, df, dt)

        # PayrollRun レコードを作成
        run = PayrollRun.objects.create(
            store=store,
            period_start=df,
            period_end=dt,
            created_by=request.user,
            overlap_warning=overlap,
            note=note,
        )

        # --- 集計（キャストは常に全員） ---
        attendance_sq = (
            CastDailySummary.objects.filter(
                store_id=sid,
                cast_id=OuterRef("pk"),
                work_date__range=(df, dt),
            )
            .values("cast_id")
            .annotate(total=Coalesce(Sum("worked_min"), Value(0)))
            .values("total")[:1]
        )

        hourly_sq = (
            CastDailySummary.objects.filter(
                store_id=sid,
                cast_id=OuterRef("pk"),
                work_date__range=(df, dt),
            )
            .values("cast_id")
            .annotate(total=Coalesce(Sum("payroll"), Value(0)))
            .values("total")[:1]
        )

        back_sq = (
            CastPayout.objects.filter(
                cast_id=OuterRef("pk"),
                bill__table__store_id=sid,
                bill__closed_at__date__range=(df, dt),
            )
            .values("cast_id")
            .annotate(total=Coalesce(Sum("amount"), Value(0)))
            .values("total")[:1]
        )

        casts = (
            Cast.objects.filter(store_id=sid)
            .annotate(
                worked_min=Coalesce(Subquery(attendance_sq), Value(0)),
                hourly_total=Coalesce(Subquery(hourly_sq), Value(0)),
                back_total=Coalesce(Subquery(back_sq), Value(0)),
            )
            .order_by("stage_name", "id")
        )

        # --- DBへ保存（サマリ） ---
        lines = []
        for c in casts:
            worked_min = int(c.worked_min or 0)
            hourly_total = int(c.hourly_total or 0)
            back_total = int(c.back_total or 0)
            lines.append(
                PayrollRunLine(
                    run=run,
                    cast=c,
                    worked_min=worked_min,
                    hourly_pay=hourly_total,
                    commission=back_total,
                    total=hourly_total + back_total,
                )
            )
        PayrollRunLine.objects.bulk_create(lines)

        # --- バック根拠明細（CastPayout “全部”） ---
        payout_qs = (
            CastPayout.objects.filter(
                bill__table__store_id=sid,
                bill__closed_at__date__range=(df, dt),
            )
            .select_related("cast", "bill", "bill_item")
            .order_by("cast__stage_name", "bill__closed_at", "id")
        )

        back_rows = []
        for p in payout_qs:
            back_rows.append(
                PayrollRunBackRow(
                    run=run,
                    cast=p.cast,
                    bill_id=p.bill_id,
                    bill_item_id=p.bill_item_id,
                    occurred_at=p.bill.closed_at if p.bill else None,
                    amount=p.amount,
                )
            )
        PayrollRunBackRow.objects.bulk_create(back_rows)

        # --- 勤務(時給)明細（CastDailySummary “全部”） ---
        daily_qs = (
            CastDailySummary.objects.filter(
                store_id=sid,
                work_date__range=(df, dt),
            )
            .select_related("cast")
            .order_by("cast__stage_name", "work_date", "id")
        )

        # キャスト別に束ねる
        daily_by_cast = {}
        for d in daily_qs:
            daily_by_cast.setdefault(d.cast_id, []).append(d)

        payouts_by_cast = {}
        for p in payout_qs:
            payouts_by_cast.setdefault(p.cast_id, []).append(p)

        # --- CSV書き出し（exp.csv 形式：1テーブル） ---
        output = io.StringIO()
        writer = csv.writer(output)

        # 1行目：ヘッダ
        _row(writer, CSV_COLUMNS)

        # 任意：メモや注意を入れたい場合は “ヘッダの次行” に入れる（空でOK）
        # 今回は exp.csv に合わせて「入れない」方針。
        # ただし将来必要なら、ここに「区分=メモ」行を追加すると自然。

        for c in casts:
            cast_id = c.id
            cast_name = c.stage_name or f"cast-{cast_id}"

            hourly_total = int(c.hourly_total or 0)
            back_total = int(c.back_total or 0)
            total = hourly_total + back_total

            # サマリ行（出勤/売上欄は空）
            _row(
                writer,
                [
                    cast_name,
                    hourly_total,
                    back_total,
                    total,
                    "", "", "", "", "", "", "", "", "", "", "", "", "",
                ],
            )

            # 出勤明細（区分=出勤日時）
            d_list = daily_by_cast.get(cast_id, [])
            if d_list:
                for d in d_list:
                    worked_min = int(d.worked_min or 0)
                    hours = _round_hours(worked_min)
                    wage_amount = int(d.payroll or 0)

                    # できるだけ “あるなら使う” 方針（無ければ空）
                    in_dt = getattr(d, "clock_in_at", None) or getattr(d, "started_at", None) or getattr(d, "check_in_at", None)
                    out_dt = getattr(d, "clock_out_at", None) or getattr(d, "ended_at", None) or getattr(d, "check_out_at", None)

                    # それらが無い場合は、work_date を出勤欄に置く（最低限の明細として成立）
                    if not in_dt and not out_dt:
                        in_dt = d.work_date

                    # 時給がスナップされているなら優先。無ければ推定（給与/時間）。
                    hourly_snap = getattr(d, "hourly_wage_snap", None)
                    if hourly_snap is None:
                        est_hourly = int(round(wage_amount / hours)) if hours else ""
                    else:
                        est_hourly = int(hourly_snap or 0)

                    _row(
                        writer,
                        [
                            "", "", "", "",
                            "出勤日時",
                            _fmt_dt(in_dt),
                            _fmt_dt(out_dt),
                            hours if hours else 0,
                            est_hourly,
                            wage_amount,
                            "", "", "", "", "", "", "",
                        ],
                    )
            else:
                _row(
                    writer,
                    [
                        "", "", "", "",
                        "出勤日時",
                        "", "", "", "", "",
                        "", "", "", "", "", "", "",
                    ],
                )

            # 売上（バック）明細（区分=売上）
            p_list = payouts_by_cast.get(cast_id, [])
            if p_list:
                for p in p_list:
                    bill_id = p.bill.id if p.bill else ""
                    item_id = p.bill_item.id if p.bill_item else ""
                    item_name = p.bill_item.name if p.bill_item else ""

                    unit_price = (
                        getattr(p.bill_item, "unit_price", None)
                        or getattr(p.bill_item, "price", None)
                        or getattr(p.bill_item, "amount", None)
                    )
                    qty = (
                        getattr(p.bill_item, "qty", None)
                        or getattr(p.bill_item, "quantity", None)
                        or getattr(p.bill_item, "count", None)
                    )

                    unit_price_i = _safe_int(unit_price, default=0)
                    qty_i = _safe_int(qty, default=0)

                    # 小計がモデルにあれば優先、無ければ unit_price * qty が作れれば計算
                    subtotal = getattr(p.bill_item, "subtotal", None) or getattr(p.bill_item, "total", None)
                    if subtotal is None and unit_price_i and qty_i:
                        subtotal_i = unit_price_i * qty_i
                    else:
                        subtotal_i = _safe_int(subtotal, default=0)

                    _row(
                        writer,
                        [
                            "", "", "", "",
                            "売上",
                            "", "", "", "", "",
                            bill_id,
                            item_id,
                            item_name,
                            unit_price_i,
                            qty_i,
                            subtotal_i,
                            int(p.amount or 0),
                        ],
                    )
            else:
                _row(
                    writer,
                    [
                        "", "", "", "",
                        "売上",
                        "", "", "", "", "",
                        "", "", "", "", "", "", "",
                    ],
                )

            # キャスト区切り（空行）
            _row(writer, [""] * len(CSV_COLUMNS))

        filename = f"payroll_{df.isoformat()}_{dt.isoformat()}.csv"
        csv_text = output.getvalue()
        output.close()

        resp = HttpResponse(
            content="\ufeff" + csv_text,  # UTF-8 BOM
            content_type="text/csv; charset=utf-8",
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp