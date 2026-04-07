<!-- BillModalPC.vue -->
<!--
  ※ 中身（script）は BillModalSP.vue と同等。SP が正の動作で、PC は 3 カラム
     レイアウトのみ差し替えた版。SP に新機能/修正が入ったら、まず SP を直し、
     その後ここの script を SP からコピーして合わせること。
-->
<script setup>
import { computed, ref, toRef, watch, nextTick, watchEffect, onMounted } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import BasicsPanel from '@/components/panel/BasicsPanel.vue'
import CustomerModal from '@/components/CustomerModal.vue'
import { useCustomers } from '@/stores/useCustomers'
import CastsPanel  from '@/components/panel/CastsPanel.vue'
import OrderPanel  from '@/components/panel/OrderPanel.vue'
import PayPanel from '@/components/panel/PayPanel.vue'
import useBillEditor from '@/composables/useBillEditor'
import { useBillCustomers } from '@/composables/useBillCustomers'
import ProvisionalPanelSP from '@/components/spPanel/ProvisionalPanelSP.vue'
import { useRoles } from '@/composables/useRoles'
import { enqueue } from '@/utils/txQueue'
import {
  api, addBillItem, updateBillCustomers, updateBillTable, updateBillCasts,
  fetchBill, deleteBillItem, patchBillItem, patchBillItemQty, fetchMasters,
  createBill, patchBill,
  setBillDiscountByCode, updateBillDiscountRule, settleBill, fetchBillTags,
  addSubstituteItem,
 } from '@/api'

const { hasRole } = useRoles()
const canProvisional = computed(() => hasRole(['manager','owner']))

// ===== ref 先行宣言 =====
const memoRef = ref('')
const displayNameRef = ref('')
const applyServiceChargeRef = ref(true)
const applyTaxRef = ref(true)
const billTags = ref([])
const selectedTagIds = ref([])
const selectedCustomerId = ref(null)
const tableIds = ref([])
const billCustomersComposable = useBillCustomers()

const props = defineProps({
  modelValue: Boolean,
  bill: { type: Object, default: null },
  serviceRate: { type: Number, default: 0.3 },
  taxRate:    { type: Number, default: 0.1 },
})
const emit = defineEmits(['update:modelValue','saved','updated','closed'])

// ===== stay 形状ユーティリティ =====
function getStayCastId(s) {
  return Number(s?.cast?.id ?? s?.cast_id ?? s?.cast ?? null)
}
function isActiveStay(s) { return !s?.left_at }
function activeStays() {
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  return stays.filter(isActiveStay)
}
function recomputeFreeIds() {
  return Array.from(new Set(
    activeStays().filter(s => s.stay_type === 'free').map(getStayCastId).filter(Boolean)
  ))
}
function recomputeHelpIds() {
  return Array.from(new Set(
    activeStays().filter(s => s.stay_type === 'free' && s.is_help === true).map(getStayCastId).filter(Boolean)
  ))
}

// ===== createBill 後の props.bill 同期 =====
function applyBillPatchToLocal(patch) {
  if (!patch || !props.bill) return
  if (patch.id != null) props.bill.id = patch.id
  if (patch.opened_at !== undefined) props.bill.opened_at = patch.opened_at
  if (patch.expected_out !== undefined) props.bill.expected_out = patch.expected_out
  if (patch.apply_service_charge !== undefined) props.bill.apply_service_charge = patch.apply_service_charge
  if (patch.apply_tax !== undefined) props.bill.apply_tax = patch.apply_tax
  if (patch.table !== undefined) props.bill.table = patch.table
  if (patch.table_atom_ids !== undefined) props.bill.table_atom_ids = patch.table_atom_ids
  if (patch.table_atoms !== undefined) props.bill.table_atoms = patch.table_atoms
  if (patch.table_label !== undefined) props.bill.table_label = patch.table_label
  const moneyKeys = ['subtotal','service_charge','tax','grand_total','total','paid_cash','paid_card','settled_total']
  for (const k of moneyKeys) { if (patch[k] !== undefined) props.bill[k] = patch[k] }
  if (patch.discount_rule !== undefined) props.bill.discount_rule = patch.discount_rule
  if (patch.manual_discounts !== undefined) props.bill.manual_discounts = patch.manual_discounts
  if (patch.memo !== undefined) props.bill.memo = patch.memo
  if (patch.display_name !== undefined) props.bill.display_name = patch.display_name
  if (patch.closed_at !== undefined) props.bill.closed_at = patch.closed_at
}

// ===== 初期化 =====
const storeSlug = ref('')
const normalizeSlug = s => String(s || '').trim().toLowerCase().replace(/_/g, '-')

async function initOnOpen() {
  pane.value = 'base'
  rightTab.value = 'order'
  await refreshStoreSlug()
  try {
    billTags.value = await fetchBillTags({ is_active: true })
  } catch (e) {
    console.warn('[BillModalPC] fetch bill tags failed', e)
    billTags.value = []
  }
  memoRef.value = props.bill?.memo ?? ''
  displayNameRef.value = props.bill?.display_name ?? ''
  selectedTagIds.value = props.bill?.tags?.map(t => t.id) || []
  resetPaymentFromProps()
  syncChargeFlagsFromBill()

  ensureServedByDefaultOnOpen()

  syncingTableInit.value = true
  const initTid = props.bill?.table?.id ?? props.bill?.table ?? null
  if (initTid != null) ed.tableId.value = Number(initTid)

  const initTids =
    props.bill?.table_atom_ids ??
    props.bill?.table_ids ??
    props.bill?.tables ??
    []

  let ids = Array.isArray(initTids) ? initTids.map(Number).filter(Boolean) : []
  if (!ids.length) {
    const t0 = props.bill?.table?.id ?? props.bill?.table ?? null
    if (t0 != null) ids = [Number(t0)]
  }
  tableIds.value = ids

  await nextTick()
  syncingTableInit.value = false
}

function ensureServedByDefaultOnOpen() {
  const casts = currentCastsForPanel.value || []
  if (!casts.length) return
  const ids = casts.map(c => Number(c.id))
  const cur = Number(ed.servedByCastId?.value || 0) || null
  if (cur && ids.includes(cur)) return
  if (ed.servedByCastId) ed.servedByCastId.value = ids[0]
}

async function refreshStoreSlug() {
  try {
    const { data } = await api.get('billing/stores/me/')
    storeSlug.value = normalizeSlug(data?.slug)
    if (storeSlug.value) localStorage.setItem('store_slug', storeSlug.value)
  } catch (e) {
    console.warn('[storeSlug] fetch failed', e)
    storeSlug.value = normalizeSlug(localStorage.getItem('store_slug') || '')
  }
}

onMounted(async () => {
  const ls = localStorage.getItem('store_slug')
  if (ls) storeSlug.value = normalizeSlug(ls)
})

const visible = computed({
  get: () => props.modelValue,
  set: v  => emit('update:modelValue', v)
})
// SP 互換: pane（PCでは prov 切替のみで使用、レイアウトには使わない）
const pane = ref('base')
// PC 専用: 右ペインの 注文/会計 切替
const rightTab = ref('order')
const isOrderTab = computed(() => rightTab.value === 'order')
const isBillTab  = computed(() => rightTab.value === 'pay' || rightTab.value === 'bill')

watch(visible, async v => {
  if (v) await initOnOpen()
}, { immediate: false })

watch(() => props.bill?.id, async (billId) => {
  if (billId && visible.value) {
    await billCustomersComposable.fetchBillCustomers(billId)
    selectedCustomerId.value = null
  }
}, { immediate: true })

watch(() => props.bill?.table_atom_ids, (v) => {
  if (!visible.value) return
  const ids = Array.isArray(v) ? v.map(Number).filter(Boolean) : []
  if (ids.length) tableIds.value = ids
}, { deep: true })

watch(() => props.bill?.table?.store, () => {
  if (visible.value) refreshStoreSlug()
})

const ed = useBillEditor(toRef(props,'bill'))

const seatType = ref('main')
function onSeatTypeChange (v) { seatType.value = v || 'main' }

const syncingTableInit = ref(false)

const seatTypeOptions = computed(() => {
  const tbls = ed.tables?.value || []
  const set = new Set(tbls.map(t => t?.seat_type || 'main'))
  if (!set.size) return [
    { code:'main', label:'メイン' },
    { code:'counter', label:'カウンター' },
    { code:'box', label:'ボックス' },
  ]
  const label = c => (c==='main' ? 'メイン' : c==='counter' ? 'カウンター' : c==='box' ? 'ボックス' : c)
  return Array.from(set).map(code => ({ code, label: label(code) }))
})

const masterMap = ref({})
async function ensureMasters(){
  if (Object.keys(masterMap.value).length) return
  const prim = (ed.masters?.value && ed.masters.value.length) ? ed.masters.value : null
  const raw  = prim || await fetchMasters()
  const arr  = Array.isArray(raw) ? raw : (raw?.results ?? [])
  const dict = {}
  for (const m of arr) {
    const code = String(m?.code ?? '').trim()
    if (!code) continue
    for (const v of [code, code.toLowerCase(), code.replace(/[-_]/g,'').toLowerCase()]) dict[v] = m
  }
  masterMap.value = dict
}
const getMasterId = (code, ...alts) => {
  const map = masterMap.value
  const cand = [code, ...alts].filter(Boolean).map(s=>String(s))
  for (const k of cand) {
    for (const n of [k, k.toLowerCase(), k.replace(/[-_]/g,'').toLowerCase()]) {
      if (map[n]?.id) return map[n].id
    }
  }
  console.warn('[master not found candidates]', cand)
  return null
}

watch(() => ed.tableId.value, async (tid, prev) => {
  if (syncingTableInit.value) return
  const nextTid = Number(tid) || null
  if (!nextTid) return
  const cur = Number(props.bill?.table?.id) || Number(props.bill?.table) || null
  if (cur && nextTid === cur) return
  if (!props.bill?.id) {
    const list = ed.tables.value || []
    props.bill.table = list.find(t => Number(t.id) === nextTid) || { id: nextTid }
    return
  }
  try {
    await updateBillTable(props.bill.id, nextTid)
    const list = ed.tables.value || []
    props.bill.table = list.find(t => Number(t.id) === nextTid) || { id: nextTid }
  } catch (e) {
    console.error('[BillModalPC] updateBillTable failed', e)
    ed.tableId.value = cur
    alert('テーブルの更新に失敗しました')
  }
})

async function ensureBillId () {
  if (props.bill?.id) return props.bill.id
  let tableIdsPayload = []
  if (tableIds.value && tableIds.value.length > 0) {
    tableIdsPayload = tableIds.value.map(Number)
  } else {
    const tableId =
      Number(ed.tableId.value) ||
      Number(props.bill?.table?.id) ||
      Number(props.bill?.table) ||
      Number(props.bill?.table_id_hint) ||
      null
    if (!tableId) { alert('テーブルが未選択です'); throw new Error('no table') }
    tableIdsPayload = [tableId]
  }
  const paxPayload =
    Number(props.bill?.pax) ||
    Number(ed.pax?.value) ||
    Number(paxFromItems.value) ||
    0

  const req = {
    table_ids: tableIdsPayload,
    expected_out: props.bill?.expected_out ?? null,
    pax: paxPayload,
    apply_service_charge: props.bill?.apply_service_charge !== false,
    apply_tax: props.bill?.apply_tax !== false,
    display_name: String(displayNameRef.value || props.bill?.display_name || ''),
  }
  const b = await createBill(req)
  applyBillPatchToLocal(b)
  return b.id
}

async function onApplySet (payload){
  await ensureMasters()
  const billId = await ensureBillId()
  for (const ln of payload.lines.filter(l => l.type==='set')) {
    if (!ln.qty) continue
    let mid
    if (ln.code === 'setMale' || ln.code === 'setFemale') {
      mid = getMasterId(
        ln.code,
        ln.code === 'setMale' ? 'setmale'   : 'setfemale',
        ln.code === 'setMale' ? 'set-male'  : 'set-female'
      )
    } else {
      mid = getMasterId(ln.code)
    }
    if (!mid) { console.warn('master not found:', ln.code); continue }
    await addBillItem(billId, { item_master: mid, qty: ln.qty })
  }
  for (const ln of payload.lines.filter(l => l.type==='addon')) {
    if (!ln.qty) continue
    const mid = getMasterId(ln.code, 'addonnight', 'night')
    if (!mid) { console.warn('addon master not found:', ln.code); continue }
    await addBillItem(billId, { item_master: mid, qty: ln.qty })
  }
  if (payload.discount_code) {
    await setBillDiscountByCode(billId, payload.discount_code)
  } else {
    await updateBillDiscountRule(billId, null)
  }
  const totalPaxFromPayload = payload.lines
    .filter(l => l.type === 'set')
    .reduce((sum, l) => sum + Number(l.qty || 0), 0)
  if (totalPaxFromPayload > 0) {
    await patchBill(billId, { pax: totalPaxFromPayload })
    await billCustomersComposable.fetchUntilCount(billId, totalPaxFromPayload)
  }
  const fresh = await fetchBill(billId).catch(()=>null)
  if (fresh) {
    applyBillPatchToLocal(fresh)
    props.bill.items = fresh.items
    props.bill.stays = fresh.stays
    emit('updated', fresh)
  }
}

async function onSaveDiscount(payload) {
  try {
    const billId = await ensureBillId()
    const body = {}
    if (payload && 'discount_rule' in payload) body.discount_rule = payload.discount_rule
    if (payload && Array.isArray(payload.manual_discounts)) body.manual_discounts = payload.manual_discounts
    await settleBill(billId, body)
    const fresh = await fetchBill(billId).catch(()=>null)
    if (fresh) {
      applyBillPatchToLocal(fresh)
      props.bill.items = fresh.items
      props.bill.stays = fresh.stays
      emit('updated', fresh)
    }
  } catch (e) {
    console.error('[BillModalPC] onSaveDiscount failed', e)
    alert('割引の保存に失敗しました')
  }
}

const maleFromItems = computed(() =>
  (props.bill?.items || []).reduce((s,it) => s + (String(it.code)==='setMale'   ? Number(it.qty||0) : 0), 0)
)
const femaleFromItems = computed(() =>
  (props.bill?.items || []).reduce((s,it) => s + (String(it.code)==='setFemale' ? Number(it.qty||0) : 0), 0)
)
const paxFromItems = computed(() => maleFromItems.value + femaleFromItems.value)

watch([maleFromItems, femaleFromItems], ([m,f]) => {
  if (ed?.pax) ed.pax.value = m + f
}, { immediate:true })

const onChooseCourse = async (opt) => {
  const res = await ed.chooseCourse(opt)
  if (res?.updated) emit('updated', props.bill.id)
}
const onDutyIds = computed(() => Array.from(ed.onDutySet?.value ?? []))
const masterNameMap = computed(() => {
  const list = ed.masters?.value || []; const map = {}
  for (const m of list) if (m && m.id != null) map[String(m.id)] = m.name
  return map
})
const masterPriceMap = computed(() => {
  const list = ed.masters?.value || []; const map = {}
  for (const m of list) if (m && m.id != null) map[String(m.id)] = m.price_regular ?? null
  return map
})
const servedByOptions = computed(() => {
  return currentCastsForPanel.value.map(c => ({
    id: c.id,
    label: c.stage_name || `cast#${c.id}`
  }))
})
const servedByMap = computed(() => { const map = {}; for (const c of servedByOptions.value || []) map[String(c.id)] = c.label; return map })

const normalizeCastId = (v) => {
  if (v == null || v === '') return null
  if (typeof v === 'number' || typeof v === 'string') {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }
  if (typeof v === 'object') {
    const cand = v.id ?? v.value ?? v.cast_id ?? null
    const n = Number(cand)
    return Number.isFinite(n) ? n : null
  }
  return null
}
const normalizeCastIds = (ids) => {
  const src = Array.isArray(ids) ? ids : []
  const out = []
  for (const x of src) {
    const n = Number(x)
    if (!Number.isFinite(n)) continue
    if (!out.includes(n)) out.push(n)
  }
  return out
}

const servedByCastIdModel = computed({
  get: () => normalizeCastId(ed.servedByCastId?.value),
  set: (v) => {
    const n = normalizeCastId(v)
    if (ed.servedByCastId) ed.servedByCastId.value = n
  }
})
const servedByCastIdsModel = computed({
  get: () => {
    const ids = normalizeCastIds(ed.servedByCastIds?.value)
    if (ids.length) return ids
    const first = normalizeCastId(ed.servedByCastId?.value)
    return first != null ? [first] : []
  },
  set: (v) => {
    const ids = normalizeCastIds(v)
    if (ed.servedByCastIds) ed.servedByCastIds.value = ids
    if (ed.servedByCastId) ed.servedByCastId.value = ids.length ? ids[0] : null
  }
})

watch(
  () => ed.servedByCastId?.value,
  (v) => {
    const n = normalizeCastId(v)
    if (v !== n && ed.servedByCastId) ed.servedByCastId.value = n
  },
  { immediate: true }
)

/* ========== 税・サービス料トグル ========== */
function syncChargeFlagsFromBill() {
  const b = props.bill || {}
  applyServiceChargeRef.value = b?.apply_service_charge !== false
  applyTaxRef.value = b?.apply_tax !== false
}
watch(() => props.bill?.apply_service_charge, (v) => { applyServiceChargeRef.value = v !== false })
watch(() => props.bill?.apply_tax, (v) => { applyTaxRef.value = v !== false })

async function patchChargeFlags(payload) {
  if (!props.bill?.id) return null
  const updated = await patchBill(props.bill.id, payload)
  if (updated) {
    applyBillPatchToLocal(updated)
    emit('updated', updated)
  }
  return updated
}

async function onApplyServiceChange(v) {
  const next = !!v
  const prev = applyServiceChargeRef.value
  applyServiceChargeRef.value = next
  if (props.bill) props.bill.apply_service_charge = next
  if (!props.bill?.id) return
  try { await patchChargeFlags({ apply_service_charge: next }) }
  catch (e) {
    console.error('[BillModalPC] failed to update apply_service_charge', e)
    applyServiceChargeRef.value = prev
    if (props.bill) props.bill.apply_service_charge = prev
    alert('サービス料の設定を更新できませんでした')
  }
}
async function onApplyTaxChange(v) {
  const next = !!v
  const prev = applyTaxRef.value
  applyTaxRef.value = next
  if (props.bill) props.bill.apply_tax = next
  if (!props.bill?.id) return
  try { await patchChargeFlags({ apply_tax: next }) }
  catch (e) {
    console.error('[BillModalPC] failed to update apply_tax', e)
    applyTaxRef.value = prev
    if (props.bill) props.bill.apply_tax = prev
    alert('TAXの設定を更新できませんでした')
  }
}

async function onMemoChange(v) {
  const next = String(v || '')
  memoRef.value = next
  if (props.bill) props.bill.memo = next
  if (!props.bill?.id) return
  try { await patchBill(props.bill.id, { memo: next }) }
  catch (e) { console.error('[BillModalPC] failed to update memo', e) }
}
async function onDisplayNameChange(v) {
  const next = String(v || '')
  displayNameRef.value = next
  if (props.bill) props.bill.display_name = next
  if (!props.bill?.id) return
  try { await patchBill(props.bill.id, { display_name: next }) }
  catch (e) { console.error('[BillModalPC] failed to update display_name', e) }
}
async function onSelectedTagIdsChange(v) {
  selectedTagIds.value = v || []
  if (props.bill) props.bill.tags = billTags.value.filter(t => selectedTagIds.value.includes(t.id))
  if (!props.bill?.id) return
  try { await patchBill(props.bill.id, { tag_ids: selectedTagIds.value }) }
  catch (e) {
    console.error('[BillModalPC] failed to update tag_ids', e)
    selectedTagIds.value = props.bill?.tags?.map(t => t.id) || []
  }
}

/* ========== Pay 周り ========== */
const displayGrandTotal = computed(() => {
  const b = props.bill || {}
  return Number((b.total != null && b.total > 0) ? b.total : (b.grand_total ?? 0))
})
const extMinutesView = computed(() => {
  const b = props.bill || {}
  const items = Array.isArray(b.items) ? b.items : []
  if (!items.length) return 0
  let mins = 0
  for (const it of items) {
    const code = String(it?.code || it?.item_master?.code || '').toLowerCase()
    if (!code.includes('extension')) continue
    const dur = Number(it.duration_min || it?.item_master?.duration_min || 30)
    const qty = Number(it.qty || 0)
    mins += Math.max(0, dur) * Math.max(0, qty)
  }
  return mins || Number(b.ext_minutes || 0) || 0
})
const payCurrent = computed(() => {
  const b = props.bill || {}
  const sub  = Number(b.subtotal       ?? 0)
  const svc  = Number(b.service_charge ?? 0)
  const tax  = Number(b.tax            ?? 0)
  const total = Number((b.total != null && b.total > 0) ? b.total
                       : (b.grand_total ?? (sub + svc + tax)))
  return { sub, svc, tax, total }
})
const paidCashRef     = ref(props.bill?.paid_cash ?? 0)
const paidCardRef     = ref(props.bill?.paid_card ?? 0)
const cardBrandRef    = ref(props.bill?.card_brand ?? null)
const settledTotalRef = ref(props.bill?.settled_total ?? (props.bill?.grand_total || 0))
const paidTotal   = computed(() => (Number(paidCashRef.value)||0) + (Number(paidCardRef.value)||0))
const targetTotal = computed(() => {
  const s = settledTotalRef.value
  return (s != null && s !== '' && Number.isFinite(Number(s))) ? Number(s) : Number(displayGrandTotal.value) || 0
})
const diff        = computed(() => paidTotal.value - targetTotal.value)
const overPay     = computed(() => Math.max(0, diff.value))
const canClose    = computed(() => targetTotal.value > 0 && paidTotal.value >= targetTotal.value)
const payRef = ref(null)

watch(() => props.bill?.memo, v => { memoRef.value = v ?? '' })
watch(() => props.bill?.display_name, v => { displayNameRef.value = v ?? '' })

function resetPaymentFromProps() {
  const b = props.bill || {}
  paidCashRef.value     = Number(b.paid_cash ?? 0) || 0
  paidCardRef.value     = Number(b.paid_card ?? 0) || 0
  cardBrandRef.value    = b.card_brand ?? null
  settledTotalRef.value = Number(b.settled_total ?? (b.grand_total || 0)) || 0
  memoRef.value         = b.memo ?? ''
  displayNameRef.value  = b.display_name ?? ''
  selectedTagIds.value  = b.tags?.map(t => t.id) || []
  syncChargeFlagsFromBill()
}

let _prevBillId = props.bill?.id ?? null
watch(() => props.bill?.id, (nowId) => {
  if (nowId == null) return
  if (_prevBillId !== nowId) {
    resetPaymentFromProps()
    _prevBillId = nowId
  }
})

const incItem = async (it) => {
  try{
    const newQty = (Number(it.qty)||0) + 1
    await patchBillItemQty(props.bill.id, it.id, newQty)
    it.qty = newQty
    it.subtotal = (masterPriceMap.value[String(it.item_master)] || 0) * newQty
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    if (fresh) {
      applyBillPatchToLocal(fresh)
      props.bill.items = fresh.items
      props.bill.stays = fresh.stays
      emit('updated', fresh)
    } else { emit('updated', props.bill.id) }
  }catch(e){ console.error(e); alert('数量を増やせませんでした') }
}
const decItem = async (it) => {
  try{
    const newQty = (Number(it.qty)||0) - 1
    if (newQty <= 0) {
      if (!confirm('削除しますか？')) return
      await deleteBillItem(props.bill.id, it.id)
    } else {
      await patchBillItemQty(props.bill.id, it.id, newQty)
      it.qty = newQty
      it.subtotal = (masterPriceMap.value[String(it.item_master)] || 0) * newQty
    }
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    if (fresh) {
      applyBillPatchToLocal(fresh)
      props.bill.items = fresh.items
      props.bill.stays = fresh.stays
      emit('updated', fresh)
    } else { emit('updated', props.bill.id) }
  }catch(e){ console.error('[decItem] error:', e); alert('数量を減らせませんでした') }
}
const changeServedBy = async ({ item, castIds, castId }) => {
  try {
    const ids = normalizeCastIds(
      Array.isArray(castIds) ? castIds : (castId != null ? [castId] : [])
    )
    await patchBillItem(props.bill.id, item.id, {
      served_by_cast_ids: ids,
      served_by_cast_id: ids.length ? ids[0] : null,
    })
    const fresh = await fetchBill(props.bill.id).catch(() => null)
    if (fresh) {
      applyBillPatchToLocal(fresh)
      props.bill.items = fresh.items
      props.bill.stays = fresh.stays
      emit('updated', fresh)
    }
  } catch (e) {
    console.error('[changeServedBy] failed', e)
    alert('担当者の変更に失敗しました')
  }
}
const removeItem = async (it) => {
  try{
    await deleteBillItem(props.bill.id, it.id)
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    if (fresh) {
      applyBillPatchToLocal(fresh)
      props.bill.items = fresh.items
      props.bill.stays = fresh.stays
      emit('updated', fresh)
    } else { emit('updated', props.bill.id) }
  }catch(e){ console.error(e); alert('削除に失敗しました') }
}

const setSettledTotal = (v) => { settledTotalRef.value = Number(v) || 0 }
const setPaidCash     = (v) => { paidCashRef.value     = Number(v) || 0 }
const setPaidCard     = (v) => { paidCardRef.value     = Number(v) || 0 }
function fillRemainderToCard(){
  const need = Math.max(0, targetTotal.value - (Number(paidCashRef.value)||0))
  paidCardRef.value = need
}

function onUpdateTimes({ opened_at, expected_out}){
  if (opened_at !== undefined)  props.bill.opened_at  = opened_at
  if (expected_out !== undefined) props.bill.expected_out = expected_out
  if (props.bill?.id) {
    enqueue('patchBill', { id: props.bill.id, payload: { opened_at, expected_out }})
    enqueue('reconcile', { id: props.bill.id })
  }
}

function onUpdatePax(newPax) {
  if (newPax !== undefined) {
    props.bill.pax = newPax
    ed.pax.value = newPax
  }
}

function onCustomersChanged() {
  if (props.bill?.id) billCustomersComposable.fetchBillCustomers(props.bill.id)
}

const customers = useCustomers()

const showCustModal = ref(false)
const activeCustId  = ref(null)
function openCustModal(id = null) {
  activeCustId.value = typeof id === 'object' && id ? id.id : id
  showCustModal.value = true
}
function handleCustPickedPC(cust) { showCustModal.value = false }
function handleCustSavedPC(cust) { showCustModal.value = false }

watch(() => billCustomersComposable.customers.value, async (bcs) => {
  if (!bcs?.length) return
  const custId = bcs[0].customer_id ?? bcs[0].customer
  if (custId && !customers.cache.get(custId)) await customers.fetchOne(custId)
}, { immediate: true })

const receiptNameForBill = computed(() => {
  const bcs = billCustomersComposable.customers.value || []
  if (!bcs.length) return ''
  const custId = bcs[0].customer_id ?? bcs[0].customer
  if (!custId) return ''
  const cust = customers.cache.get(custId)
  if (!cust) return ''
  return cust.receipt_name || cust.full_name || ''
})

function onUpdateTableIds(ids) {
  const nextIds = Array.isArray(ids)
    ? ids.map(Number).filter(v => Number.isFinite(v))
    : []
  tableIds.value = nextIds
  if (ed?.tableId) ed.tableId.value = nextIds.length ? nextIds[0] : null
  if (props.bill?.id) {
    enqueue('patchBill', { id: props.bill.id, payload: { tableIds: nextIds }})
    enqueue('reconcile', { id: props.bill.id })
  }
}

async function onDiscountRuleChange(ruleId) {
  if (!props.bill?.id) return
  const billId = props.bill.id
  try {
    props.bill.discount_rule = ruleId
    await updateBillDiscountRule(billId, ruleId)
    const fresh = await fetchBill(billId).catch(() => null)
    if (fresh) emit('updated', fresh)
  } catch (e) {
    console.error('[BillModalPC] failed to update discount rule', e)
    alert('割引の適用に失敗しました')
  }
}

const historyEvents = computed(() => {
  const b = props.bill || {}
  const out = []
  for (const s of (b.stays || [])) {
    const cid = getStayCastId(s) || 'unknown'
    const name = s?.cast?.stage_name
    const avatar = s?.cast?.avatar_url
    out.push({ key: `in-${cid}-${s.entered_at}`, when: s.entered_at, name, avatar, stayTag: s.stay_type, ioTag: 'in' })
    if (s.left_at) {
      out.push({ key: `out-${cid}-${s.left_at}`, when: s.left_at, name, avatar, stayTag: s.stay_type, ioTag: 'out' })
    }
  }
  out.sort((a, b) => new Date(b.when) - new Date(a.when))
  return out
})

const closing = ref(false)
const deleting = ref(false)

async function confirmClose(){
  if (closing.value || !props.bill?.id) return
  if (!window.confirm('本当に会計しますか？')) return
  closing.value = true
  try{
    await nextTick()
    const billId   = props.bill.id
    const memoFromPanel = (payRef.value?.getMemo?.() ?? '').toString()
    const disc = payRef.value?.getDiscountEntry?.() || { label: null, amount: 0 }
    const memoStr = disc.amount > 0
      ? `${memoFromPanel}\n割引明細: ${disc.label} / 金額: ¥${disc.amount.toLocaleString()}`
      : memoFromPanel
    const settled  = Number(settledTotalRef.value) || Number(displayGrandTotal.value) || 0
    const paidCash = Number(paidCashRef.value) || 0
    const paidCard = Number(paidCardRef.value) || 0
    const cardBrand = cardBrandRef.value ?? null
    const rows = payRef.value?.getManualDiscounts?.() || []

    props.bill.paid_cash     = paidCash
    props.bill.paid_card     = paidCard
    props.bill.card_brand    = cardBrand
    props.bill.settled_total = settled
    props.bill.memo          = memoStr
    props.bill.closed_at     = new Date().toISOString()
    try{
      const { useBills } = await import('@/stores/useBills')
      const bs = useBills()
      const i = bs.list.findIndex(b => Number(b.id) === Number(billId))
      if (i >= 0) {
        const nowISO = new Date().toISOString()
        bs.list[i] = { ...bs.list[i],
          paid_cash: paidCash, paid_card: paidCard, card_brand: cardBrand, settled_total: settled,
          memo: memoStr,
          closed_at: nowISO,
          stays: (bs.list[i].stays || []).map(s => s.left_at ? s : ({ ...s, left_at: nowISO })),
        }
      }
    }catch{}

    const helpIds = recomputeHelpIds()
    enqueue('patchBill', { id: billId, payload: {
      paid_cash: paidCash,
      paid_card: paidCard,
      card_brand: cardBrand,
      memo: memoStr,
      discount_rule: props.bill?.discount_rule ? Number(props.bill.discount_rule) : null,
      manual_discounts: rows,
      settled_total: settled,
      help_ids: helpIds,
    }})
    enqueue('closeBill', { id: billId, payload: { settled_total: settled }})
    enqueue('reconcile', { id: billId })

    emit('saved', { id: billId })
    visible.value = false
    pane.value = 'base'
    {
      const nowISO = new Date().toISOString()
      props.bill.stays = (props.bill.stays || []).map(s => s.left_at ? s : ({ ...s, left_at: nowISO }))
    }
    alert('会計が完了しました')
  }catch(e){
    console.error(e)
    alert('会計に失敗しました（オフラインでも後で確定されます）')
  }finally{
    closing.value = false
  }
}

async function confirmDelete(){
  if (deleting.value) return
  const billId = props.bill?.id
  if (!billId) {
    visible.value = false
    pane.value = 'base'
    return
  }
  if (!window.confirm('この伝票を削除します。よろしいですか？')) return
  deleting.value = true
  try {
    try {
      const { useBills } = await import('@/stores/useBills')
      const bs = useBills()
      bs.list = (bs.list || []).filter(b => Number(b.id) !== Number(billId))
    } catch {}
    enqueue('deleteBill', { id: billId })
    enqueue('reconcile', { id: billId })
    emit('saved', { id: billId, deleted: true })
    visible.value = false
    pane.value = 'base'
    alert('伝票を削除しました')
  } catch (e) {
    console.error('[BillModalPC] delete failed', e)
    alert('伝票の削除に失敗しました')
  } finally {
    deleting.value = false
  }
}

const currentCastsForPanel = computed(() => {
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  const actives = stays.filter(s => !s.left_at)
  const byId = new Map((ed.currentCasts?.value || []).map(c => [Number(c.id), c]))
  return actives
    .map(s => {
      const id = getStayCastId(s)
      if (!id) return null
      const base = byId.get(id) || {
        id,
        stage_name: s?.cast?.stage_name || `cast#${id}`,
        avatar_url: s?.cast?.avatar_url || null
      }
      return {
        id,
        stage_name: base.stage_name,
        avatar_url: base.avatar_url,
        stay_type: s.stay_type,
        inhouse: s.stay_type === 'in',
        dohan: s.stay_type === 'dohan',
        is_honshimei: s.stay_type === 'nom',
        is_help: !!s.is_help,
      }
    })
    .filter(Boolean)
})

watch(() => currentCastsForPanel.value, (casts) => {
  if (!casts || casts.length === 0) return
  const currentIds = casts.map(c => c.id)
  const currentSelected = ed.servedByCastId?.value
  if (currentSelected && currentIds.includes(currentSelected)) return
  if (ed.servedByCastId) ed.servedByCastId.value = casts[0].id
}, { immediate: true })

watch(() => ed.servedByCastId?.value, (newCastId) => {
  if (!newCastId || !ed.pending?.value) return
  ed.pending.value.forEach(item => {
    if (item && item.cast_id == null) {
      item.cast_id = newCastId
      if (!Array.isArray(item.cast_ids) || item.cast_ids.length === 0) {
        item.cast_ids = [Number(newCastId)]
      }
    }
  })
})

function updateStayLocal(castId, next) {
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  const t = stays.find(s => !s.left_at && getStayCastId(s) === Number(castId))
  const nowISO = new Date().toISOString()
  if (t) {
    t.stay_type = next.stay_type
    t.is_help   = !!next.is_help
    if (next.entered_at) t.entered_at = next.entered_at
  } else {
    props.bill.stays = [
      ...stays,
      { cast:{ id:Number(castId), stage_name:`cast#${castId}` },
        stay_type: next.stay_type, is_help: !!next.is_help,
        entered_at: nowISO, left_at: null }
    ]
  }
}

async function onSetMain(castId){
  updateStayLocal(castId, { stay_type:'nom', is_help:false })
  try { await ed.setMain(Number(castId)) } catch {}
}

async function onSetMainWithCustomer(payload){
  const { castId, customerId } = payload
  if (!castId || !customerId) return
  updateStayLocal(castId, { stay_type:'nom', is_help:false })
  if (ed.mainIds && !ed.mainIds.value.includes(Number(castId))) {
    ed.mainIds.value = [...ed.mainIds.value, Number(castId)]
  }
  if (ed.freeIds) ed.freeIds.value = ed.freeIds.value.filter(id => Number(id) !== Number(castId))
  if (ed.dohanIds) ed.dohanIds.value = ed.dohanIds.value.filter(id => Number(id) !== Number(castId))

  if (props.bill?.id) {
    const requestPayload = { customer_id: Number(customerId), cast_ids: [Number(castId)] }
    try {
      await api.post(`/billing/bills/${props.bill.id}/nominations/`, requestPayload)
    } catch (e) {
      console.error('[BillModalPC] POST nominations 失敗', e)
      alert('本指名の登録に失敗しました')
      updateStayLocal(castId, { stay_type:'free', is_help:false })
      if (ed.mainIds) ed.mainIds.value = ed.mainIds.value.filter(id => Number(id) !== Number(castId))
      if (ed.freeIds && !ed.freeIds.value.includes(Number(castId))) {
        ed.freeIds.value = [...ed.freeIds.value, Number(castId)]
      }
    }
  }
}

async function onSetFree(castId){
  updateStayLocal(castId, { stay_type:'free', is_help:false })
  try { await ed.setFree(Number(castId)) } catch {}
}
async function onSetInhouse(castId){
  updateStayLocal(castId, { stay_type:'in', is_help:false })
  try { await ed.setInhouse(Number(castId)) } catch {}
  const nowHelpIds = recomputeHelpIds()
  const nowFreeIds = recomputeFreeIds()
  if (!props.bill?.id) return
  enqueue('patchBill', { id: props.bill.id, payload: { free_ids: nowFreeIds, help_ids: nowHelpIds } })
  enqueue('reconcile', { id: props.bill.id })
}
async function onSetDohan(castId){
  updateStayLocal(castId, { stay_type:'dohan', is_help:false })
  try { await ed.setDohan(Number(castId)) } catch {}
}
async function onRemoveCast(castId){
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  const t = stays.find(s => !s.left_at && getStayCastId(s) === Number(castId))
  if (t) t.left_at = new Date().toISOString()
  try { await ed.removeCast(Number(castId)) } catch {}
}
async function onSetHelp(castId) {
  if (!props.bill?.id) return
  const billId = props.bill.id
  updateStayLocal(castId, { stay_type:'free', is_help:true })
  const freeIds = recomputeFreeIds()
  const helpIds = recomputeHelpIds()
  enqueue('patchBill', { id: billId, payload: { free_ids: freeIds, help_ids: helpIds }})
  enqueue('reconcile', { id: billId })
}

function normalizeHelpBeforeSave(){
  let changed = false
  for (const s of (props.bill?.stays || [])) {
    if (!s.left_at && s.is_help && s.stay_type !== 'free') {
      s.is_help = false
      changed = true
    }
  }
  if (changed) {
    const ids = recomputeHelpIds()
    enqueue('patchBill', { id: props.bill.id, payload: { help_ids: ids } })
    enqueue('reconcile', { id: props.bill.id })
  }
}

const saving = ref(false)
async function handleSave(){
  if (saving.value) return
  saving.value = true
  try{
    normalizeHelpBeforeSave()
    const optimistic = await ed.save()
    emit('saved', optimistic)
  }finally{
    saving.value = false
  }
}

async function onAddSubstitute(masterId) {
  if (!props.bill?.id) return
  const castId = servedByCastIdsModel.value.length ? servedByCastIdsModel.value[0] : servedByCastIdModel.value
  if (!castId) { alert('キャストを選択してください'); return }
  try {
    await addSubstituteItem(props.bill.id, {
      item_master_id: Number(masterId),
      cast_id: Number(castId),
      qty: 1,
      ...(selectedCustomerId.value ? { customer_id: Number(selectedCustomerId.value) } : {}),
    })
    emit('updated', props.bill.id)
  } catch (e) {
    console.error('substitute add failed', e)
    alert('立替追加に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

function handleClose() {
  emit('saved', props.bill)
  visible.value = false
  pane.value = 'base'
}
</script>

<template>
  <BaseModal v-if="bill" v-model="visible" class="billmodal-pc">
    <template #header>
      <div id="header" class="header-bar d-flex align-items-center justify-content-between p-2">
        <div class="page-title fs-4 fw-bold">伝票</div>
        <div class="button-area d-flex gap-2 fs-5">
          <button class="btn btn-sm btn-outline-danger" :disabled="deleting" @click="confirmDelete" aria-label="delete"><IconTrash /></button>
          <button class="btn btn-sm btn-primary" :disabled="saving" @click="handleSave" aria-label="save"><IconDeviceFloppy /></button>
          <button class="btn btn-sm btn-light" @click="handleClose" aria-label="close"><IconX /></button>
        </div>
      </div>
    </template>

    <div class="billmodal-pc-body">
      <!-- 左ペイン: 基本情報 -->
      <div class="bm-col">
        <div class="outer">
          <BasicsPanel
            :bill-id="props.bill?.id"
            :tables="ed.tables.value || []"
            :table-id="ed.tableId.value"
            :table-ids="tableIds"
            :current-casts="currentCastsForPanel"
            :course-options="ed.courseOptions.value || []"
            :seat-type-options="seatTypeOptions"
            :seat-type="seatType"
            :show-customer="true"
            :customer="ed.selectedCustomer.value"
            :customer-name="ed.customerName.value"
            :customer-results="ed.custResults.value"
            :customer-searching="ed.custLoading.value"
            :opened-at="bill.opened_at"
            :expected-out="bill.expected_out"
            :ext-minutes="extMinutesView"
            :set-rounds="bill.set_rounds || 0"
            :pax="bill.pax ?? paxFromItems"
            :male="maleFromItems"
            :female="femaleFromItems"
            :apply-service="applyServiceChargeRef"
            :apply-tax="applyTaxRef"
            :memo="memoRef"
            :display-name="displayNameRef"
            :tags="billTags"
            :selected-tag-ids="selectedTagIds"
            :history-events="historyEvents"
            :bill-customers-from-parent="(billCustomersComposable.customers.value?.length > 0) ? billCustomersComposable.customers.value : null"
            @update-times="onUpdateTimes"
            @update:seatType="onSeatTypeChange"
            @update:tableId="v => (ed.tableId.value = v)"
            @update:tableIds="onUpdateTableIds"
            @update:pax="onUpdatePax"
            @update:applyService="onApplyServiceChange"
            @update:applyTax="onApplyTaxChange"
            @update:memo="onMemoChange"
            @update:display-name="onDisplayNameChange"
            @update:selectedTagIds="onSelectedTagIdsChange"
            @chooseCourse="(opt, qty) => onChooseCourse(opt, qty)"
            @clearCustomer="ed.clearCustomer"
            @searchCustomer="ed.searchCustomers"
            @pickCustomer="ed.pickCustomerInline"
            @applySet="onApplySet"
            @save="handleSave"
            @customers-changed="onCustomersChanged"
            @edit-customer="openCustModal"
          />
        </div>
      </div>

      <!-- 中央ペイン: キャスト -->
      <div class="bm-col">
        <div class="outer">
          <CastsPanel
            :current-casts="currentCastsForPanel"
            :bench-casts="ed.benchCasts.value"
            :on-duty-ids="onDutyIds"
            :keyword="ed.castKeyword.value"
            :history-events="historyEvents"
            :bill-id="props.bill?.id"
            :bill-customers="billCustomersComposable.customers.value || []"
            @update:keyword="v => (ed.castKeyword.value = v)"
            @setFree="onSetFree"
            @setInhouse="onSetInhouse"
            @setDohan="onSetDohan"
            @setMain="onSetMain"
            @setMainWithCustomer="onSetMainWithCustomer"
            @removeCast="onRemoveCast"
            @setHelp="onSetHelp"
            @save="handleSave"
          />
        </div>
      </div>

      <!-- 右ペイン: 注文 / 会計 / 仮 切替（左カラムと同じアンダーラインタブ） -->
      <div class="bm-col">
        <div class="right-tabs sticky-top bg-white" role="tablist">
          <button type="button" class="rt-btn" :class="{ active: rightTab === 'order' }" @click="rightTab='order'">
            注文
          </button>
          <button type="button" class="rt-btn" :class="{ active: rightTab === 'pay' }" @click="rightTab='pay'">
            会計
          </button>
          <button v-if="canProvisional" type="button" class="rt-btn"
                  :class="{ active: rightTab === 'prov' }" @click="rightTab='prov'">
            仮
          </button>
        </div>

        <div class="outer">
          <OrderPanel
            v-show="rightTab === 'order'"
            :cat-options="ed.orderCatOptions.value || []"
            :selected-cat="ed.selectedOrderCat.value"
            :order-masters="ed.orderMasters.value || []"
            v-model:served-by-cast-id="servedByCastIdModel"
            v-model:served-by-cast-ids="servedByCastIdsModel"
            :pending="ed.pending.value"
            :master-name-map="masterNameMap"
            :served-by-map="servedByMap"
            :served-by-options="servedByOptions"
            :master-price-map="masterPriceMap"
            :bill-customers="billCustomersComposable.customers.value || []"
            :selected-customer-id="selectedCustomerId"
            :bill-id="props.bill?.id"
            :bill-closed="!!props.bill?.closed_at"
            @update:selectedCat="v => (ed.selectedOrderCat.value = v)"
            @update:selectedCustomerId="v => (selectedCustomerId = v)"
            @addPending="(id, qty, castIds, customerId) => {
              const q = Math.max(1, Number(qty || 1))
              const ids = (Array.isArray(castIds) ? castIds : []).map(Number).filter(Number.isFinite)
              ed.pending.value.push({
                master_id: Number(id),
                qty: q,
                cast_ids: ids,
                cast_id: ids.length ? ids[0] : null,
                customer_id: (customerId == null || customerId === '') ? null : Number(customerId)
              })
            }"
            @removePending="i => ed.pending.value.splice(i,1)"
            @clearPending="() => (ed.pending.value = [])"
            @placeOrder="handleSave"
            @addSubstitute="onAddSubstitute"
          />

          <PayPanel
            v-show="rightTab === 'pay'"
            ref="payRef"
            :bill-id="props.bill?.id"
            :bill="props.bill"
            :pane="rightTab"
            :items="bill.items || []"
            :substitute-items="bill.substitute_items || []"
            :master-name-map="masterNameMap"
            :served-by-map="servedByMap"
            :served-by-options="servedByOptions"
            :bill-opened-at="bill.opened_at || ''"
            :current="payCurrent"
            :display-grand-total="displayGrandTotal"
            :memo="props.bill?.memo || ''"
            :tags="props.bill?.tags || []"
            :settled-total="settledTotalRef"
            :paid-cash="paidCashRef"
            :paid-card="paidCardRef"
            :card-brand="cardBrandRef"
            :diff="diff"
            :over-pay="overPay"
            :can-close="canClose"
            :discount-rule-id="props.bill?.discount_rule ? Number(props.bill.discount_rule) : null"
            :manual-discounts="props.bill?.manual_discounts || []"
            :store-slug="storeSlug"
            :dosukoi-discount-unit="1000"
            :receipt-name="receiptNameForBill"
            @update:settledTotal="setSettledTotal"
            @update:paidCash="setPaidCash"
            @update:paidCard="setPaidCard"
            @update:cardBrand="v => (cardBrandRef = v)"
            @fillRemainderToCard="fillRemainderToCard"
            @confirmClose="confirmClose"
            @incItem="incItem"
            @decItem="decItem"
            @deleteItem="removeItem"
            @changeServedBy="changeServedBy"
            @update:discountRule="onDiscountRuleChange"
            @saveDiscount="onSaveDiscount"
          />

          <ProvisionalPanelSP
            v-show="rightTab === 'prov' && canProvisional"
            :key="`prov-${props.bill?.id || 'new'}`"
            :bill="props.bill || {}"
            :ed="ed"
            :service-rate="props.serviceRate"
            :tax-rate="props.taxRate"
          />
        </div>
      </div>
    </div>

    <!-- 顧客情報編集モーダル -->
    <CustomerModal
      v-model="showCustModal"
      :customer-id="activeCustId"
      @picked="handleCustPickedPC"
      @saved="handleCustSavedPC"
    />
  </BaseModal>
</template>

<style scoped lang="scss">
/* PC モーダル本体：フル幅 + 3 等分グリッド + ページ全体で 1 つの縦スクロール */
.billmodal-pc {
  :deep(.modal-dialog),
  :deep(.modal-fullscreen) {
    max-width: 100vw !important;
    width: 100vw !important;
    margin: 0 !important;
  }
  :deep(.modal-content) {
    overflow-x: hidden;
    width: 100%;
  }
  :deep(.modal-body) {
    display: block !important;       /* d-flex を解除 */
    overflow-x: hidden;
    width: 100%;
    padding: 0.5rem 1rem;
  }
}
.billmodal-pc-body {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;  /* フル幅で 3 等分 */
  gap: 1rem;
  width: 100%;
  align-items: start;
}
.billmodal-pc-body .bm-col {
  min-width: 0;                        /* グリッド子のはみ出し防止 */
}
.billmodal-pc-body .outer {
  background: #fff;
  border-radius: 8px;
  padding: 0.75rem;
  overflow: visible;
  min-width: 0;
}
/* 右ペイン: 左カラムと同じアンダーラインタブ（カラム幅いっぱいで等分割） */
.right-tabs {
  display: flex;
  width: 100%;
  border-bottom: 1px solid #e9ecef;
  padding: 0.5rem 0 0;
  top: 0;
  z-index: 5;
}
.right-tabs .rt-btn {
  flex: 1 1 0;
  border: none;
  background: transparent;
  color: #6c757d;
  font-size: 1rem;
  font-weight: 600;
  padding: 0.5rem 0.25rem;
  margin-bottom: -1px;
  border-bottom: 2px solid transparent;
  text-align: center;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.right-tabs .rt-btn:hover { color: #000; }
.right-tabs .rt-btn.active {
  color: #000;
  border-bottom-color: #000;
}
</style>
