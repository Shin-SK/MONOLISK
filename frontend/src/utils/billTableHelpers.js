// src/utils/billTableHelpers.js

/** bill から使用中テーブルID配列を返す（M2M優先、legacy FK互換） */
export function tableIdsOfBill(b) {
  if (Array.isArray(b?.table_atom_ids) && b.table_atom_ids.length)
    return b.table_atom_ids.map(Number)
  const t = b?.table
  if (t == null) return []
  return [typeof t === 'object' ? Number(t.id) : Number(t)]
}

/** billsリストからM2M対応の openBillMap (tableId -> bill) を生成 */
export function buildOpenBillMap(bills) {
  const m = new Map()
  bills.forEach(b => {
    if (b.closed_at) return
    for (const tid of tableIdsOfBill(b)) m.set(tid, b)
  })
  return m
}

/** bill のテーブル表示ラベルを生成 (例: "A+B", "3") */
export function billTableLabel(bill, tablesById) {
  const ids = tableIdsOfBill(bill)
  if (!ids.length) return '卓なし'
  return ids
    .map(id => tablesById.get(id)?.number ?? id)
    .join('+')
}
