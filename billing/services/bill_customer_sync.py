# billing/services/bill_customer_sync.py
"""
Bill.pax と BillCustomer の同期機能。
pax が更新されたときに、不足分の BillCustomer を自動追加する。
"""
from django.db import transaction
from django.utils import timezone
from typing import Optional

from billing.models import Bill, BillCustomer, Customer


def ensure_bill_customers_for_pax(bill: Bill) -> int:
    """
    Bill.pax に合わせて、不足分の BillCustomer を作成する。

    Args:
        bill (Bill): 対象の伝票

    Returns:
        int: 新たに作成した BillCustomer の件数

    Algorithm:
        1. target = max(0, bill.pax)
        2. current = BillCustomer.objects.filter(bill=bill).count()
        3. if target > current:
               (target - current) 件の BillCustomer を作成する
        4. else:
               何もしない（削除しない）
    """
    with transaction.atomic():
        # 現在の件数を確認（念のため atomic 内で重複チェック）
        target = max(0, int(bill.pax or 0))
        current = BillCustomer.objects.filter(bill=bill).count()

        if target <= current:
            # 既に足りている、または pax が小さくなった → 何もしない
            return 0

        # 不足分を計算
        shortage = target - current

        # 不足分の BillCustomer を作成
        # stub Customer を作成（既存の signals.attach_customer_and_snapshot と同じ方式）
        to_create = []
        for _ in range(shortage):
            stub = Customer.objects.create()
            to_create.append(
                BillCustomer(
                    bill=bill,
                    customer=stub,
                    arrived_at=timezone.now(),  # 明確に「今」を指定
                    left_at=None,
                )
            )

        BillCustomer.objects.bulk_create(to_create)
        return len(to_create)
