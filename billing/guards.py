"""
Phase 2: Bill store ownership guard functions.
Unified permission checking for bill.table dependencies.
"""
from rest_framework.exceptions import PermissionDenied


def bill_belongs_to_store(bill, store_id):
    """
    Check if a Bill belongs to the given store.
    Handles both legacy FK (table) and M2M (tables) cases.
    """
    # Legacy FK path
    if bill.table_id:
        return bill.table.store_id == store_id
    
    # M2M path
    return bill.tables.filter(store_id=store_id).exists()


def assert_bill_in_store(bill, store_id):
    """
    Assert that bill belongs to store_id, raise PermissionDenied otherwise.
    """
    if not bill_belongs_to_store(bill, store_id):
        raise PermissionDenied("Bill does not belong to your store")
