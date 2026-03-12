# billing/services/substitute.py
"""
立替額計算サービス

方針:
- 基本ルール: 税抜価格 ÷ 5 の切り捨て
- シャンパン特例: 原価を 100円単位で切り上げ
- シャンパンで原価未設定(NULL/0)の場合: 基本ルールにフォールバック（安全側）
- シャンパン判定: ItemCategory.code == 'champagne'
- 将来カテゴリ特例・商品個別特例が増える想定だが、今回はハードコード
"""
import math


def is_champagne(item_master) -> bool:
    if not item_master or not hasattr(item_master, 'category'):
        return False
    return getattr(item_master.category, 'code', None) == 'champagne'


def calc_substitute_unit(item_master) -> int:
    """
    商品1個あたりの立替額を計算する。

    Returns:
        int: 立替額（円）
    """
    if is_champagne(item_master):
        cost = item_master.cost
        if cost and cost > 0:
            # 原価を100円単位で切り上げ
            return int(math.ceil(float(cost) / 100)) * 100
        # 原価未設定 → 基本ルールにフォールバック

    # 基本: 税抜価格 ÷ 5 の切り捨て
    price = item_master.price_regular or 0
    return int(price // 5)


def calc_substitute_total(item_master, qty: int) -> int:
    """
    立替額 × 数量 の合計を返す。
    """
    return calc_substitute_unit(item_master) * qty
