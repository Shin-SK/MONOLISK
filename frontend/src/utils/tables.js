/**
 * tableLabelFromAtoms(atoms)
 * 文字列配列またはオブジェクト配列を両対応で処理。
 * @param {Array} atoms - ['A', 'B'] または [{id, name}, ...] または [{id, number}, ...] など
 * @returns {string} - テーブル名をアルファベット順にソートして連結した文字列（例：'AB'）
 */
export function tableLabelFromAtoms(atoms) {
  if (!atoms || !atoms.length) return ''
  const names = atoms.map(a => {
    if (typeof a === 'string') return a
    // {name}, {number}, {code} のいずれかが来ても拾えるよう冗長化
    return a.name ?? a.number ?? a.code ?? ''
  }).filter(Boolean)
  return names.sort().join('')
}

/**
 * computeComboSeq(bills)
 * bills の配列に対して、display_label フィールドを追加。
 * 同じ table_label を持つ bills に対して連番を付与する。
 *
 * @param {Array} bills - Bill オブジェクトの配列
 * @returns {Array} - display_label フィールドを持つ bills の配列
 */
export function computeComboSeq(bills) {
  const counter = Object.create(null)
  return (bills || []).map(b => {
    const key = b.table_label || tableLabelFromAtoms(b.table_atoms)
    counter[key] = (counter[key] || 0) + 1
    const seq = counter[key]
    return { ...b, display_label: key + (seq > 1 ? String(seq) : '') }
  })
}
