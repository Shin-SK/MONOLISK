"""
本指名プール除外判定フック

目的：
    本指名プール計算（卓小計×時間区間×折半）において、
    店舗ごとに「除外カテゴリ」を後付けできるようにするための判定関数。

設計方針：
    - Base は「全部載せ」（exclude_from_payout=False のみで判定）
    - Store override で「TCカテゴリ除外」などの追加ルールを適用
    - この関数に除外ロジックを集約することで、計算箇所から切り離して安全に変更可能

フェーズ1（現在）：
    - 常に False を返す（=何も除外しない）
    - 既存挙動を変更しない
    - フックの位置だけを確定

将来の拡張：
    - ItemCategory.exclude_from_nom_pool フラグを追加（A案）
    - または Store.nom_pool_exclude_codes 配列を追加（B案）
    - TC（テーブルチャージ）などのカテゴリを除外する
"""


def should_exclude_from_nom_pool(item) -> bool:
    """
    本指名プールから除外すべきかを判定する
    
    Args:
        item: BillItem インスタンス
        
    Returns:
        True: プールから除外する
        False: プールに含める
        
    フェーズ3実装：
        ItemCategory.exclude_from_nom_pool フラグを見る
        
    将来の拡張例：
        # B案：Store に除外カテゴリコード配列を持たせる場合
        store = item.bill.table.store
        if store.nom_pool_exclude_codes:
            category_code = item.item_master.category.code if item.item_master and item.item_master.category else None
            return category_code in store.nom_pool_exclude_codes
    """
    # フェーズ3：ItemCategory のフラグを見る
    if item.item_master and item.item_master.category:
        return item.item_master.category.exclude_from_nom_pool
    return False
