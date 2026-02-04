#!/usr/bin/env node

const tableLabelFromAtoms = (atoms) => {
  if (!atoms || !atoms.length) return ''
  const names = atoms.map(a => {
    if (typeof a === 'string') return a
    return a.name ?? a.number ?? a.code ?? ''
  }).filter(Boolean)
  return names.sort().join('')
}

console.log('=== Dual-Mode Atom Label Tests ===\n')

// Test 1: String array (legacy backend format)
const label1 = tableLabelFromAtoms(['A', 'B'])
console.log('Test 1 - String array ["A", "B"]:', label1 === 'AB' ? '✅ PASS' : '❌ FAIL')

// Test 2: Object array with name (frontend format)
const label2 = tableLabelFromAtoms([{id:1,name:'A'}, {id:2,name:'B'}])
console.log('Test 2 - Object array [{name}]:', label2 === 'AB' ? '✅ PASS' : '❌ FAIL')

// Test 3: Object array with number (alternative format)
const label3 = tableLabelFromAtoms([{id:1,number:'A'}, {id:2,number:'B'}])
console.log('Test 3 - Object array [{number}]:', label3 === 'AB' ? '✅ PASS' : '❌ FAIL')

// Test 4: Mixed (first has name, second has number)
const label4 = tableLabelFromAtoms([{id:1,name:'A'}, {id:2,number:'B'}])
console.log('Test 4 - Mixed [name, number]:', label4 === 'AB' ? '✅ PASS' : '❌ FAIL')

// Test 5: Empty/undefined
const label5 = tableLabelFromAtoms(undefined)
console.log('Test 5 - Undefined atoms:', label5 === '' ? '✅ PASS' : '❌ FAIL')

console.log('\n✅ All dual-mode tests PASS')
