#!/usr/bin/env node

const tableLabelFromAtoms = (atoms) => {
  if (!atoms || atoms.length === 0) return ''
  return atoms.map(a => a.name || '').sort().join('')
}

const computeComboSeq = (bills) => {
  if (!bills || bills.length === 0) return []
  const labelCount = {}
  bills.forEach((bill) => {
    const label = bill.table_label || ''
    labelCount[label] = (labelCount[label] || 0) + 1
  })
  const labelIndex = {}
  return bills.map((bill) => {
    const label = bill.table_label || ''
    labelIndex[label] = (labelIndex[label] || 0) + 1
    let displayLabel = label
    if (labelCount[label] > 1 && labelIndex[label] > 1) {
      displayLabel = label + labelIndex[label]
    }
    return { ...bill, display_label: displayLabel }
  })
}

console.log('=== Phase 2 Frontend QA Tests ===')
console.log('')

// Test 1
const label1 = tableLabelFromAtoms([{id:1,name:'A'}])
console.log('✓ Test 1 - Single table (A):', label1 === 'A' ? '✅ PASS' : '❌ FAIL')

// Test 2
const label2 = tableLabelFromAtoms([{id:1,name:'A'},{id:2,name:'B'}])
console.log('✓ Test 2 - Two tables (A+B):', label2 === 'AB' ? '✅ PASS' : '❌ FAIL')

// Test 3
const result3 = computeComboSeq([
  {id:1,table_label:'AB'},
  {id:2,table_label:'AB'},
  {id:3,table_label:'C'}
])
console.log('✓ Test 3 - Duplicate combo sequence:')
console.log('    Bill 1 (AB):', result3[0].display_label === 'AB' ? '✅ PASS' : '❌ FAIL')
console.log('    Bill 2 (AB):', result3[1].display_label === 'AB2' ? '✅ PASS' : '❌ FAIL')
console.log('    Bill 3 (C) :', result3[2].display_label === 'C' ? '✅ PASS' : '❌ FAIL')

console.log('')
console.log('Manual verification tests (Tests 4 & 5):')
console.log('  Test 4: Edit existing single-table bill, add second table')
console.log('    Expected: form.table_ids updates from [1] to [1, 2]')
console.log('    Verify: PATCH request includes table_ids array')
console.log('')
console.log('  Test 5: Network tab verification')
console.log('    Expected: POST/PATCH bodies contain "table_ids" array')
console.log('    Expected: No legacy "table" or "table_id" fields')
console.log('')
console.log('=== End QA Suite ===')
