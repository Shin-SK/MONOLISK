"""
billing/services/nomination_summary.py

本指名期間の卓小計を計算するサービス
- 本指名客の到着〜退店時間帯に、その卓で注文されたアイテムの合計
- 複数本指名の場合は人数で均等折半
"""
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from datetime import datetime

from billing.models import Bill, BillCustomerNomination, BillCustomer, BillItem


def build_nomination_summaries(bill: Bill, now: datetime | None = None) -> list[dict]:
    """
    本指名顧客ごとの「滞在期間内の卓小計」を計算する
    
    Args:
        bill: 対象の伝票
        now: 現在時刻（nowが無い場合は end とする）。指定なしなら timezone.now()
    
    Returns:
        list of dict with keys:
        - customer_id
        - customer_name
        - period_start (arrived_at)
        - period_end (left_at or now)
        - period_status ('complete' | 'ongoing')
        - subtotal (区間内の卓小計・Decimal)
        - cast_ids (本指名キャスト ID リスト)
        - num_casts (本指名数)
        - per_cast_share (per_cast_share = subtotal / num_casts、Decimal)
    """
    if now is None:
        now = timezone.now()
    
    results = []
    
    # bill に紐づくすべての本指名をグループ化：customer -> [cast_ids]
    nomination_groups = {}
    
    nominations = BillCustomerNomination.objects.filter(bill=bill).select_related('customer', 'cast')
    
    if not nominations.exists():
        # 本指名がない場合は空リスト
        return []
    
    for nom in nominations:
        if nom.customer_id not in nomination_groups:
            nomination_groups[nom.customer_id] = {
                'customer': nom.customer,
                'cast_ids': [],
            }
        nomination_groups[nom.customer_id]['cast_ids'].append(nom.cast_id)
    
    # 各顧客について、滞在期間と卓小計を計算
    for customer_id, nom_info in nomination_groups.items():
        customer = nom_info['customer']
        cast_ids = nom_info['cast_ids']
        num_casts = len(cast_ids)
        
        # BillCustomer から滞在期間を取得
        try:
            bill_customer = BillCustomer.objects.get(bill=bill, customer=customer)
        except BillCustomer.DoesNotExist:
            # 顧客が bill に参加していない場合はスキップ
            # （通常はあり得ない、validation済みのため）
            continue
        
        arrived_at = bill_customer.arrived_at
        left_at = bill_customer.left_at
        
        # arrived_at が None の場合は集計対象外
        if arrived_at is None:
            # 0扱いでもいいが、仕様上は対象外とする
            continue
        
        # left_at が None の場合は now を使用
        period_end = left_at if left_at is not None else now
        period_status = 'complete' if left_at is not None else 'ongoing'
        
        # 区間 [arrived_at, period_end) の BillItem を集計
        # ★重要★ customer で絞らない（卓小計なので）
        items_in_period = BillItem.objects.filter(
            bill=bill,
            ordered_at__gte=arrived_at,
            ordered_at__lt=period_end,
        )
        
        # 卓小計を計算
        subtotal = Decimal('0')
        for item in items_in_period:
            subtotal += Decimal(str(item.subtotal))
        
        # 本指名数で均等折半
        if num_casts > 0:
            per_cast_share = subtotal / Decimal(str(num_casts))
            # Decimal の丸め: ROUND_HALF_UP を使って小数点第2位までにする
            per_cast_share = per_cast_share.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            per_cast_share = Decimal('0')
        
        # 結果を追加
        results.append({
            'customer_id': customer.id,
            'customer_name': customer.display_name,
            'period_start': arrived_at,
            'period_end': period_end,
            'period_status': period_status,
            'subtotal': str(subtotal),  # JSON対応でも Decimal 文字列で返す
            'cast_ids': cast_ids,
            'num_casts': num_casts,
            'per_cast_share': str(per_cast_share),
        })
    
    return results
