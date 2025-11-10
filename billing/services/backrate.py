# billing/services/backrate.py（新規ファイル）
from decimal import Decimal
from typing import Optional
from billing.models import ItemCategory, Store, Cast, CastCategoryRate

# stay_type: 'free' | 'nom' | 'in' | 'dohan'
_STAYKEY = {
    'free':  'free',
    'nom':   'nomination',
    'in':    'inhouse',
    'dohan': 'dohan',
}

def resolve_back_rate(*, store: Store, category: Optional[ItemCategory], cast: Optional[Cast], stay_type: str) -> Decimal:
    """
    優先順位:
      1) CastCategoryRate（キャスト×カテゴリ）
      2) Cast override（free/nomination/inhouse）
      3) ItemCategory（カテゴリ基準）
      4) Store 基準（今回追加：free/nomination/inhouse/dohan）
      5) 0
    """
    key = _STAYKEY.get(stay_type, 'free')

    # 1) CastCategoryRate
    if cast and category:
        ccr = CastCategoryRate.objects.filter(cast=cast, category=category).only(
            'rate_free', 'rate_nomination', 'rate_inhouse'
        ).first()
        if ccr:
            if key == 'free' and ccr.rate_free is not None:
                return Decimal(ccr.rate_free)
            if key == 'nomination' and ccr.rate_nomination is not None:
                return Decimal(ccr.rate_nomination)
            if key == 'inhouse' and ccr.rate_inhouse is not None:
                return Decimal(ccr.rate_inhouse)

    # 2) Cast override
    if cast:
        # dohan は個別override列がないためスキップ
        if key == 'free' and cast.back_rate_free_override is not None:
            return Decimal(cast.back_rate_free_override)
        if key == 'nomination' and cast.back_rate_nomination_override is not None:
            return Decimal(cast.back_rate_nomination_override)
        if key == 'inhouse' and cast.back_rate_inhouse_override is not None:
            return Decimal(cast.back_rate_inhouse_override)

    # 3) ItemCategory 基準
    if category:
        if key == 'free' and category.back_rate_free is not None:
            return Decimal(category.back_rate_free)
        if key == 'nomination' and category.back_rate_nomination is not None:
            return Decimal(category.back_rate_nomination)
        if key == 'inhouse' and category.back_rate_inhouse is not None:
            return Decimal(category.back_rate_inhouse)

    # 4) Store 基準（今回の追加でここが効くようになる）
    if store:
        if key == 'free':
            return Decimal(store.back_rate_free_default or 0)
        if key == 'nomination':
            return Decimal(store.back_rate_nomination_default or 0)
        if key == 'inhouse':
            return Decimal(store.back_rate_inhouse_default or 0)
        if key == 'dohan':
            return Decimal(store.back_rate_dohan_default or 0)

    # 5) fallback
    return Decimal('0.00')
