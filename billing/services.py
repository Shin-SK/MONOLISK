# billing/services.py

from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from typing import Set, Iterable          # 追加
from django.db.models import Sum, Case, When, IntegerField, F, Q, Value
from django.db.models.functions import Coalesce
from .models import Cast, CastPayout, Bill, BillItem, ItemMaster


# 旧ロジックが必要なら残してOKだが いまは BillCalculator を真とする
def calc_bill_totals(bill):
    items = bill.items.select_related('item_master', 'served_by_cast')
    subtotal = sum(i.subtotal for i in items)

    store = _bill_store(bill)
    if store is None:
        return {'subtotal': subtotal, 'service': 0, 'tax': 0, 'total': subtotal, 'payouts': []}

    sr = Decimal(str(store.service_rate or 0))
    tr = Decimal(str(store.tax_rate or 0))
    if sr >= 1: sr /= 100
    if tr >= 1: tr /= 100

    # 新ポリシー - サ別は小計×率 税は小計×率
    service_amt = (Decimal(subtotal) * sr).quantize(0, ROUND_FLOOR)
    tax_amt     = (Decimal(subtotal) * tr).quantize(0, ROUND_FLOOR)

    total = int(Decimal(subtotal) + service_amt + tax_amt)

    return {
        'subtotal': int(subtotal),
        'service' : int(service_amt),
        'tax'     : int(tax_amt),
        'total'   : total,
        'payouts' : [],
    }


def get_cast_sales(date_from, date_to, store_id=None):
    cast_qs = Cast.objects.all()
    if store_id:
        cast_qs = cast_qs.filter(store_id=store_id)

    period_payouts = CastPayout.objects.filter(
        bill__opened_at__date__range=(date_from, date_to)
    )

    cast_qs = (
        cast_qs
        .annotate(
            sales_nom=Coalesce(Sum(
                Case(
                    When(
                        payouts__in=period_payouts,
                        payouts__bill__stays__stay_type='nom',
                        payouts__bill__stays__cast_id=F('id'),
                        then='payouts__amount'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ), 0),
            sales_in=Coalesce(Sum(
                Case(
                    When(
                        payouts__in=period_payouts,
                        payouts__bill__stays__stay_type='in',
                        payouts__bill__stays__cast_id=F('id'),
                        then='payouts__amount'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ), 0),
            sales_free=Coalesce(Sum(
                Case(
                    When(
                        payouts__in=period_payouts,
                        payouts__bill__stays__stay_type='free',
                        payouts__bill__stays__cast_id=F('id'),
                        then='payouts__amount'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ), 0),
        )
        .annotate(total=F('sales_nom') + F('sales_in') + F('sales_free'))
        .order_by('-total')
    )

    return list(
        cast_qs.values(
            'stage_name',
            cast_id     = F('id'),
            sales_nom   = F('sales_nom'),
            sales_in    = F('sales_in'),
            sales_free  = F('sales_free'),
            sales_champ = Value(0, output_field=IntegerField()),
            total       = F('total'),
        )
    )


# 安全な store 解決 - 卓が無くても落とさない
def _bill_store(bill):
    # 1 まず卓から
    table = getattr(bill, 'table', None)
    if table and getattr(table, 'store', None):
        return table.store

    # 2 明細の ItemMaster.store
    it = bill.items.select_related('item_master__store').first()
    if it and getattr(getattr(it, 'item_master', None), 'store', None):
        return it.item_master.store

    # 3 本指名または指名キャスト
    mc = getattr(bill, 'main_cast', None)
    if mc and getattr(mc, 'store', None):
        return mc.store
    try:
        nc = bill.nominated_casts.first()
        if nc and getattr(nc, 'store', None):
            return nc.store
    except Exception:
        pass

    # 4 stays 経由の保険
    st = bill.stays.select_related('bill__table__store').first()
    if st and getattr(getattr(st, 'bill', None), 'table', None):
        return st.bill.table.store

    # 5 見つからないなら None
    return None


_MAIN_FEE_CODE    = "mainNom-fee"
_INHOUSE_FEE_CODE = "houseNom-fee"

def _sync_fee_lines(
    bill: Bill,
    cast_ids_added: Iterable[int],
    cast_ids_removed: Iterable[int],
    item_code: str,
):
    store = _bill_store(bill)
    if store is None:
        # 裸のBillは同期をスキップ - 500防止
        return

    try:
        master = ItemMaster.objects.get(store=store, code=item_code)
    except ItemMaster.DoesNotExist:
        return

    for cid in cast_ids_added:
        BillItem.objects.get_or_create(
            bill=bill,
            item_master=master,
            served_by_cast_id=cid,
            defaults=dict(
                qty=1,
                price=master.price_regular,
                exclude_from_payout=True,
                is_nomination=(item_code == _MAIN_FEE_CODE),
                is_inhouse   =(item_code == _INHOUSE_FEE_CODE),
            ),
        )

    if cast_ids_removed:
        BillItem.objects.filter(
            bill=bill,
            item_master=master,
            served_by_cast_id__in=cast_ids_removed,
        ).delete()


def sync_nomination_fees(
    bill: Bill,
    prev_main: Set[int], new_main: Set[int],
    prev_in:   Set[int], new_in:   Set[int],
):
    # mainNom-fee と houseNom-fee を差分同期
    _sync_fee_lines(
        bill,
        cast_ids_added=new_main - prev_main,
        cast_ids_removed=prev_main - new_main,
        item_code=_MAIN_FEE_CODE,
    )
    _sync_fee_lines(
        bill,
        cast_ids_added=new_in - prev_in,
        cast_ids_removed=prev_in - new_in,
        item_code=_INHOUSE_FEE_CODE,
    )
    apply_bill_calculation(bill)


from .calculator import BillCalculator

def apply_bill_calculation(bill):
    # BillCalculator の結果を Bill に反映して保存
    r = BillCalculator(bill).execute()
    bill.subtotal       = r.subtotal
    bill.service_charge = r.service_fee
    bill.tax            = r.tax
    bill.grand_total    = r.total
    bill.save(update_fields=['subtotal','service_charge','tax','grand_total'])