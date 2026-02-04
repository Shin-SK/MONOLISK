"""
Phase 2: Bill store resolution for PL/aggregation/payroll.
Unified store ID extraction from Bill (handles both FK and M2M paths).
"""


def get_bill_store_id(bill):
    """
    Get the store_id associated with a Bill.
    Handles both legacy FK (table) and M2M (tables) cases.
    
    Returns: store_id (int) or None
    """
    # Legacy FK path
    if bill.table_id:
        return bill.table.store_id
    
    # M2M path
    vals = list(bill.tables.values_list("store_id", flat=True).distinct())
    return vals[0] if vals else None
