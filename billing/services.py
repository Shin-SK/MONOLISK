from collections import defaultdict
from .models import CastPayout

def calc_bill_totals(bill):
    items = bill.items.all()
    subtotal = sum(i.subtotal for i in items)

    service_base = sum(i.subtotal for i in items if i.item_master.apply_service)
    service_amt  = round(service_base * bill.table.store.service_rate)
    tax_amt      = round((subtotal + service_amt) * bill.table.store.tax_rate)

    # ── バック計算
    payouts = defaultdict(int)
    n_nom   = bill.nominated_casts.count() or 1

    for it in items:
        if it.exclude_from_payout or it.back_rate == 0:
            continue

        amt = round(it.subtotal * it.back_rate)

        if it.is_nomination:
            share = amt // n_nom
            for c in bill.nominated_casts.all():
                payouts[c] += share
        elif it.is_inhouse and it.served_by_cast:
            payouts[it.served_by_cast] += amt
        elif not it.is_nomination and not it.is_inhouse and it.served_by_cast:
            payouts[it.served_by_cast] += amt

    return {
        'subtotal': subtotal,
        'service' : service_amt,
        'tax'     : tax_amt,
        'total'   : subtotal + service_amt + tax_amt,
        'payouts' : payouts,
    }
