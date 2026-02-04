"""
Phase2 QuerySet helpers for Bill.tables M2M migration.
Store-Locked filtering with M2M (tables) and legacy FK (table_id) support.
"""
from django.db.models import Q
from .models import Bill


def bills_in_store_qs(store_id):
    """
    Store-LockedのBill基本QuerySet。
    M2M(tables)経由 または legacy FK(table)経由 の両方を許容。
    
    NULL卓（table_id = None, tables未設定）は全店共通で拾う
    （将来の要件次第で見直す余地あり）。
    
    distinct + prefetch_related('tables') で最適化。
    """
    if not store_id:
        return Bill.objects.none()
    
    return (
        Bill.objects
        .filter(
            Q(tables__store_id=store_id) |
            Q(table__store_id=store_id) |
            Q(table_id__isnull=True)  # NULL卓は全店共通
        )
        .distinct()
        .prefetch_related('tables')
    )


def filter_by_table_atom(qs, table_id):
    """原子テーブルIDを含むBillのみを抽出"""
    if not table_id:
        return qs
    return qs.filter(tables__id=table_id).distinct()
