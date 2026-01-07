# billing/services/payout_helper.py
"""
歩合計算ヘルパー（シャンパン・原価基準対応）
"""

from decimal import Decimal
from typing import Tuple, Optional


def is_champagne(item_master) -> bool:
    """
    シャンパンかどうかを判定

    Args:
        item_master: ItemMaster instance

    Returns:
        bool: シャンパン（category.code == "champagne"）
    """
    if not item_master or not hasattr(item_master, 'category'):
        return False
    return getattr(item_master.category, 'code', None) == 'champagne'


def get_payout_base(bill_item, item_master) -> Tuple[Decimal, str, Decimal]:
    """
    歩合計算の基準値を取得

    シャンパンの場合は cost（原価）を使用し、cost が無い場合は subtotal（売価）を使用。
    その他の商品は subtotal（売価）を使用。

    Args:
        bill_item: BillItem instance
        item_master: ItemMaster instance

    Returns:
        Tuple[base_amount, basis, base_value]
        - base_amount: 計算に使用する金額（Decimal）
        - basis: 計算の基準 ("cost" or "subtotal")
        - base_value: 実際に使用した値（cost または subtotal）

    Examples:
        >>> base, basis, value = get_payout_base(bill_item, item_master)
        >>> amount = base * back_rate
        >>> # basis == "cost" ならシャンパンで原価基準で計算された
    """
    subtotal = Decimal(bill_item.subtotal or 0)

    # シャンパン判定
    if is_champagne(item_master):
        cost = Decimal(item_master.cost or 0)
        # cost が有効（> 0）なら使用、そうでなければ subtotal にフォールバック
        if cost > 0:
            return cost, "cost", cost
        else:
            return subtotal, "subtotal", subtotal
    else:
        # 通常商品は subtotal を使用
        return subtotal, "subtotal", subtotal
