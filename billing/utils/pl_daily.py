# utils/pl_daily.py
from __future__ import annotations
from datetime import date
from decimal import Decimal
from django.db.models import F, Sum, Value, IntegerField, Q, CharField 
from django.db.models.functions import Coalesce
from billing.models  import Bill, BillItem, PersonnelExpense
from billing.utils.services import cast_payroll_sum_by_business_date
from billing.calculator import BillCalculator
from billing.utils.bizday import get_business_window
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

__all__ = ["get_daily_pl"]

# 大カテゴリの定義（backward compatibility のため残す）
DRINK_CATEGORY_CODES = set(getattr(settings, "PL_DRINK_CATEGORY_CODES", {"cast-drink"}))
DRINK_ITEM_PREFIXES  = set(getattr(settings, "PL_DRINK_ITEM_PREFIXES",  set()))

def _calc_open_bill_total(bill: Bill) -> int:
    return BillCalculator(bill).execute().total


def _calculate_commission_from_snapshot(bills) -> int:
    """
    ★ Phase A: payroll_snapshot ベースで歩合を集計
    
    スナップショットから by_cast[].amount を合算。
    フォールバック：snapshot が無い Bill は BillCalculator で一時計算（DB 保存なし）。
    """
    total = 0
    
    for bill in bills:
        if bill.payroll_snapshot and isinstance(bill.payroll_snapshot, dict):
            # snapshot の by_cast 配列から amount を合算
            by_cast = bill.payroll_snapshot.get('by_cast', [])
            bill_commission = sum(int(c.get('amount', 0)) for c in by_cast)
            total += bill_commission
            logger.debug(f"[PL] Bill {bill.id}: commission from snapshot = {bill_commission}")
        else:
            # フォールバック：snapshot がない Bill は BillCalculator で一時計算
            try:
                result = BillCalculator(bill).execute()
                payouts = result.cast_payouts
                bill_commission = sum(p.amount for p in payouts)
                total += bill_commission
                logger.warning(
                    f"[PL] Bill {bill.id}: snapshot missing, calculated commission = {bill_commission} "
                    f"(will NOT save payout)"
                )
            except Exception as e:
                logger.exception(f"[PL] Bill {bill.id}: failed to calculate commission: {e}")
                bill_commission = 0
                total += bill_commission
    
    return int(total)


def get_daily_pl(target_date: date, *, store_id: int, include_breakdown: bool = False):
    """
    日次PL を major_group ベースで集計
    
    Args:
        target_date: 対象日付
        store_id: 店舗ID
        include_breakdown: 詳細な group_sales を含めるか（デフォルト False）
    
    Returns:
        dict: 売上・集計情報
    """
    # storeId が文字列で来た場合の対応
    store_id = int(store_id) if isinstance(store_id, str) else store_id
    
    start_dt, end_dt = get_business_window(target_date, store_id=store_id)

    bills = (
        Bill.objects
        .filter(closed_at__gte=start_dt, closed_at__lt=end_dt, table__store_id=store_id)
        .select_related("table__store")
        .prefetch_related("items")
    )

    subtotal_sum = (
        BillItem.objects
        .filter(bill__in=bills)
        .aggregate(s=Coalesce(Sum(F("price") * F("qty")), 0))
    )["s"] or 0

    # ★ 会計上は settled_total 優先、無ければ grand_total
    sales_total = bills.aggregate(
        s=Coalesce(Sum(Coalesce(F("settled_total"), F("grand_total"), Value(0), output_field=IntegerField())), 0)
    )["s"] or 0

    items = BillItem.objects.filter(bill__in=bills).select_related("item_master__category")

    # ─────────────── major_group ベース集計 ───────────────────
    group_sales = {}
    for major_group in ['drink', 'champagne', 'food', 'other', 'set', 'extension', 'other_fee']:
        group_items = items.filter(item_master__category__major_group=major_group)
        sales = group_items.aggregate(s=Coalesce(Sum(F("price") * F("qty")), 0))["s"] or 0
        qty = group_items.aggregate(c=Coalesce(Sum("qty"), 0))["c"] or 0
        group_sales[major_group] = {
            'sales': int(sales),
            'qty': int(qty),
        }

    # ─────────────── 主要KPI ───────────────────
    # guest_count = set グループの qty 合計
    guest_count = group_sales.get('set', {}).get('qty', 0) or 0
    
    # avg_spend = sales_total / max(guest_count, 1)
    avg_spend = int(sales_total // max(guest_count, 1))

    # drink_sales / drink_qty
    drink_sales = group_sales.get('drink', {}).get('sales', 0)
    drink_qty = group_sales.get('drink', {}).get('qty', 0)
    drink_unit_price = int(drink_sales // max(drink_qty, 1)) if drink_qty else 0

    # champagne_sales / champagne_qty
    champagne_sales = group_sales.get('champagne', {}).get('sales', 0)
    champagne_qty = group_sales.get('champagne', {}).get('qty', 0)

    # extension_sales / extension_qty
    extension_sales = group_sales.get('extension', {}).get('sales', 0)
    extension_qty = group_sales.get('extension', {}).get('qty', 0)

    # other_sales = food + other + other_fee の売上合計
    other_sales = (
        group_sales.get('food', {}).get('sales', 0) +
        group_sales.get('other', {}).get('sales', 0) +
        group_sales.get('other_fee', {}).get('sales', 0)
    )

    # ─────────────── 人件費・利益 ───────────────────
    paid_sums = bills.aggregate(
        sales_cash=Coalesce(Sum("paid_cash"), 0),
        sales_card=Coalesce(Sum("paid_card"), 0),
    )
    sales_cash = int(paid_sums["sales_cash"] or 0)
    sales_card = int(paid_sums["sales_card"] or 0)

    # ★ Phase A: 歩合を payroll_snapshot ベースで集計
    # （CastPayout 生成失敗の影響を遮断。現場の数字は snapshot/都度計算が正とする）
    commission = _calculate_commission_from_snapshot(bills)
    
    # 時給=CastDailySummary（business date）
    hourly_pay = int(cast_payroll_sum_by_business_date(target_date, target_date, store_id) or 0)
    labor_cost = int(hourly_pay + commission)
    operating_profit = int(sales_total - labor_cost)

    # ─────────────── 立替経費（参考情報） ───────────────────
    # 対象日付の立替経費を集計（policy='collect' のみ）
    collect_expenses = PersonnelExpense.objects.filter(
        subject_user__store_id=store_id,
        policy='collect',
        occurred_at__gte=start_dt,
        occurred_at__lt=end_dt,
    )
    
    personnel_expenses_collect_created = int(
        collect_expenses.aggregate(
            s=Coalesce(Sum('amount'), Value(0), output_field=IntegerField())
        )['s'] or 0
    )
    personnel_expenses_collect_settled = int(
        collect_expenses.aggregate(
            s=Coalesce(Sum('settlement_events__amount'), Value(0), output_field=IntegerField())
        )['s'] or 0
    )
    personnel_expenses_collect_outstanding = int(
        personnel_expenses_collect_created - personnel_expenses_collect_settled
    )

    result = {
        "date"             : target_date.isoformat(),
        "store_id"         : store_id,
        "guest_count"      : int(guest_count or 0),
        "subtotal"         : int(subtotal_sum),
        "sales_total"      : int(sales_total),
        "sales_cash"       : sales_cash,
        "sales_card"       : sales_card,
        "avg_spend"        : avg_spend,
        # ドリンク関連
        "drink_sales"      : int(drink_sales or 0),
        "drink_qty"        : int(drink_qty or 0),
        "drink_unit_price" : drink_unit_price,
        # シャンパン関連（新規）
        "champagne_sales"  : int(champagne_sales or 0),
        "champagne_qty"    : int(champagne_qty or 0),
        # 延長関連
        "extension_sales"  : int(extension_sales or 0),
        "extension_qty"    : int(extension_qty or 0),
        # その他売上（新規）
        "other_sales"      : int(other_sales or 0),
        # 人件費・利益
        "commission"       : commission,
        "hourly_pay"       : hourly_pay,
        "labor_cost"       : labor_cost,
        "operating_profit" : operating_profit,
        # 立替経費（参考情報）
        "personnel_expenses_collect_created"     : personnel_expenses_collect_created,
        "personnel_expenses_collect_settled"     : personnel_expenses_collect_settled,
        "personnel_expenses_collect_outstanding" : personnel_expenses_collect_outstanding,
    }

    if include_breakdown:
        result["group_sales"] = {
            k: {
                'sales': v['sales'],
                'qty': v['qty'],
            }
            for k, v in group_sales.items()
        }

    return result
