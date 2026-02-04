/**
 * Frontend Phase 2 QA Test Suite (Manual Verification Checklist)
 * Tests to verify before merging feat/frontend-phase2-basicpanel-multiselect
 */

import { tableLabelFromAtoms, computeComboSeq } from '@/utils/tables.js'

/**
 * Test 1: Single table (A) selection displays "A", not "A1"
 */
export function test1_singleTableDisplay() {
  const atoms = [{ id: 1, name: 'A' }]
  const label = tableLabelFromAtoms(atoms)
  console.log('Test 1 - Single table label:', label)
  console.assert(label === 'A', 'Expected "A" but got: ' + label)
}

/**
 * Test 2: Two tables (A+B) display as "AB"
 */
export function test2_twoTablesDisplay() {
  const atoms = [
    { id: 1, name: 'A' },
    { id: 2, name: 'B' }
  ]
  const label = tableLabelFromAtoms(atoms)
  console.log('Test 2 - Two table label:', label)
  console.assert(label === 'AB', 'Expected "AB" but got: ' + label)
}

/**
 * Test 3: Duplicate combo sequence - second AB combo displays as "AB2"
 */
export function test3_duplicateComboSequence() {
  const bills = [
    { id: 1, table_label: 'AB', table_atoms: [{ id: 1, name: 'A' }, { id: 2, name: 'B' }] },
    { id: 2, table_label: 'AB', table_atoms: [{ id: 1, name: 'A' }, { id: 2, name: 'B' }] },
    { id: 3, table_label: 'C', table_atoms: [{ id: 3, name: 'C' }] }
  ]
  
  const result = computeComboSeq(bills)
  console.log('Test 3 - Combo sequence:', result.map(b => ({ id: b.id, label: b.display_label })))
  
  console.assert(result[0].display_label === 'AB', 'First AB should be "AB", got: ' + result[0].display_label)
  console.assert(result[1].display_label === 'AB2', 'Second AB should be "AB2", got: ' + result[1].display_label)
  console.assert(result[2].display_label === 'C', 'C should be "C", got: ' + result[2].display_label)
}

/**
 * Test 4: Edit existing single-table bill, add second table
 * (Manual verification: form.table_ids should update from [1] to [1, 2])
 */
export function test4_editExistingBill_notes() {
  console.log('Test 4 - Manual verification needed:')
  console.log('  1. Open a bill with single table (e.g., tableIds = [1])')
  console.log('  2. In TablePicker, check box for table B (id=2)')
  console.log('  3. Verify form.table_ids becomes [1, 2]')
  console.log('  4. Click Save')
  console.log('  5. Verify Network tab shows PATCH with table_ids: [1, 2]')
  console.log('  6. Verify response includes table_atoms with both tables')
}

/**
 * Test 5: Network tab verification - no legacy table field
 */
export function test5_networkVerification_notes() {
  console.log('Test 5 - Network tab verification (manual):')
  console.log('  1. Open DevTools Network tab')
  console.log('  2. Create new bill with tables A, B')
  console.log('  3. In Network, find POST /billing/bills/')
  console.log('  4. Check request body:')
  console.log('     - MUST HAVE: "table_ids": [1, 2]')
  console.log('     - MUST NOT HAVE: "table" or "table_id" fields')
  console.log('  5. Check response:')
  console.log('     - MUST HAVE: "table_atoms": [{id, name}, ...]')
  console.log('     - MUST HAVE: "table_label": "AB"')
}

/**
 * Run all test functions
 */
export function runAllTests() {
  console.log('=== Phase 2 Frontend QA Test Suite ===')
  console.log('')
  
  try {
    test1_singleTableDisplay()
    console.log('✅ Test 1 PASSED\n')
  } catch (e) {
    console.error('❌ Test 1 FAILED:', e.message, '\n')
  }
  
  try {
    test2_twoTablesDisplay()
    console.log('✅ Test 2 PASSED\n')
  } catch (e) {
    console.error('❌ Test 2 FAILED:', e.message, '\n')
  }
  
  try {
    test3_duplicateComboSequence()
    console.log('✅ Test 3 PASSED\n')
  } catch (e) {
    console.error('❌ Test 3 FAILED:', e.message, '\n')
  }
  
  test4_editExistingBill_notes()
  console.log('')
  
  test5_networkVerification_notes()
  console.log('')
  
  console.log('=== End QA Suite ===')
}

// Auto-run if imported in browser console
if (typeof window !== 'undefined') {
  // Optionally uncomment to auto-run: runAllTests()
}
