# billing/constants.py
"""
ビジネスルール定数
運用に合わせて調整可能
"""

# ───────── BillItem（明細）制限 ─────────
BILLITEM_QTY_MIN = 1
BILLITEM_QTY_MAX = 99
BILLITEM_PRICE_MIN = 0
BILLITEM_PRICE_MAX = 2_000_000  # 単価上限（極端値対策）

# ───────── Bill（支払い）制限 ─────────
BILL_PAYMENT_MIN = 0
BILL_PAYMENT_MAX = 100_000_000  # 支払額上限（極端値対策）
BILL_OVERPAY_TOLERANCE = 10_000_000  # お釣りの許容範囲（grand_totalを超える上限）

# ───────── エラーメッセージ ─────────
ERROR_MESSAGES = {
    'qty_range': f'数量は {BILLITEM_QTY_MIN}〜{BILLITEM_QTY_MAX} の範囲で指定してください',
    'qty_zero': '数量は1以上で指定してください',
    'price_range': f'単価は ¥{BILLITEM_PRICE_MIN:,}〜¥{BILLITEM_PRICE_MAX:,} の範囲で指定してください',
    'price_negative': '単価は0円以上で指定してください',
    'payment_negative': '支払額は0円以上で指定してください',
    'payment_too_large': f'支払額は ¥{BILL_PAYMENT_MAX:,} 以下で指定してください',
    'overpay_excessive': f'支払合計が請求額を ¥{BILL_OVERPAY_TOLERANCE:,} 以上超えています。確認してください',
    'item_master_not_found': '指定された商品が見つかりません',
    'item_master_wrong_store': '他店舗の商品は使用できません',
}
