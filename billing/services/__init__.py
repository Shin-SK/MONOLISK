# billing/services/__init__.py
"""
給与計算サービス群（backrate, payout, pl など）

このパッケージは billing.services.backrate 等で参照可能。
同時に payroll snapshot 関連は billing.payroll.snapshot からインポート。
レガシー関数は service_utils から re-export。

Note: payroll snapshot functions are imported lazily to avoid circular imports
"""

# Re-export payroll snapshot functions for backward compatibility (lazy import)
def __getattr__(name):
    if name == 'build_payroll_snapshot' or name == 'generate_payroll_snapshot':
        from billing.payroll.snapshot import build_payroll_snapshot
        return build_payroll_snapshot
    elif name == 'compute_current_hash':
        from billing.payroll.snapshot import compute_current_hash
        return compute_current_hash
    elif name == 'is_payroll_dirty':
        from billing.payroll.snapshot import is_payroll_dirty
        return is_payroll_dirty
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Re-export legacy utility functions from service_utils
from billing.service_utils import (
    sync_nomination_fees,
    sync_dohan_fees,
    calc_bill_totals,
    get_cast_sales,
    apply_bill_calculation,
)

__all__ = [
    # snapshot functions
    'generate_payroll_snapshot',
    'compute_current_hash',
    'is_payroll_dirty',
    # legacy utility functions
    'sync_nomination_fees',
    'sync_dohan_fees',
    'calc_bill_totals',
    'get_cast_sales',
    'apply_bill_calculation',
]

