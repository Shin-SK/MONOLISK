// src/utils/draftbills.js
export function buildBillDraft({ tableId = null, tableIds = null, storeId = null } = {}) {
  const table_atom_ids = tableIds
    ? tableIds.map(Number)
    : tableId ? [Number(tableId)] : []
  return {
    id: null,
    items: [],
    customers: [],
    stays: [],
    table: null,
    table_id_hint: tableId,
    table_atom_ids,
    opened_at: null,
    expected_out: null,
    grand_total: 0,
    paid_cash: 0,
    paid_card: 0,
    set_rounds: 0,
    ext_minutes: 0,
    meta: { storeId },
  }
}

export const isBillNew = (b) => !b?.id

export function ensureCustomerIds(bill) {
  if (!bill) return bill
  if (Array.isArray(bill.customers)) {
    bill.customers = bill.customers.map(c => (c && typeof c === 'object') ? c.id : c)
  }
  return bill
}
