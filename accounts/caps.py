# accounts/caps.py
from .models import StoreRole

# 固定の機能名（フロントと共有）
ALL_CAPS = {
    # 閲覧・集計
    'view_pl_store',      # 自店PL/集計
    'view_pl_multi',      # 複数店舗PL（オーナー）
    'view_details',       # 伝票詳細・客履歴・在席/出勤の閲覧
    # 実務
    'operate_orders',     # 伝票/注文/会計/締め
    'manage_master',      # マスタ編集（メニュー等）
    'user_manage',        # 店舗ユーザー管理
    # ステーション
    'station_view',       # KDS画面の閲覧
    'station_operate',    # KDS操作（ACK/READY）
    # キャスト
    'cast_order_self',    # 本指名中の自卓注文（※オブジェクトレベルで最終判定）
}

def get_caps_for(user, store_id: int | None) -> set[str]:
    if not user.is_authenticated:
        return set()

    if user.is_superuser:
        return set(ALL_CAPS)

    caps = set()
    # store_idが無いAPI（/me等）は「横断可否」だけ先に判定
    roles = set(m.role for m in user.memberships.all())
    if StoreRole.OWNER in roles:
        caps.update({'view_pl_multi', 'view_details'})

    if store_id is None:
        return caps

    # 単一店舗の役割
    role = (user.memberships.filter(store_id=store_id)
            .values_list('role', flat=True).first())

    if role == StoreRole.MANAGER:
        caps.update({'view_pl_store','operate_orders','manage_master','user_manage',
                     'station_view','station_operate','view_details'})
    elif role == StoreRole.STAFF:
        caps.update({'view_pl_store','operate_orders','station_view','station_operate','view_details'})
    elif role == StoreRole.CAST:
        caps.update({'cast_order_self'})  # 実行時は別途オブジェクトチェック
    elif role == StoreRole.OWNER:
        # オーナーが自店に入って見る場合
        caps.update({'view_pl_store','view_details'})

    return caps
