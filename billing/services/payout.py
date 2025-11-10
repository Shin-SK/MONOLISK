# billing/services/payout.py（新規）
from decimal import Decimal
from typing import Optional
from billing.models import Store, ItemCategory, ItemMaster, Cast
from billing.services.backrate import resolve_back_rate  # 既存（％の解決）

def resolve_payout_amount(*, store: Store, category: Optional[ItemCategory],
                          item: Optional[ItemMaster], cast: Optional[Cast],
                          stay_type: str, price: int, qty: int) -> int:
    """
    free/inhouse はカテゴリで固定額がONなら『固定×数量』、それ以外は『％×金額』。
    （指名/同伴は従来どおり％のみ）
    """
    # 固定額の対象は free / inhouse のみ
    if stay_type in ('free', 'in'):
        if category and category.use_fixed_payout_free_in and category.payout_fixed_per_item is not None:
            return int(category.payout_fixed_per_item) * int(qty)

    # ％（既存）
    rate = resolve_back_rate(store=store, category=category, cast=cast, stay_type=stay_type)
    base = Decimal(price) * Decimal(qty)
    return int((base * Decimal(rate)).quantize(Decimal('1')))
