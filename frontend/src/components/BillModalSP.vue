<script setup>
import { computed, ref, toRef, watch, nextTick, watchEffect, onMounted } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import BasicsPanel from '@/components/panel/BasicsPanel.vue'
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
 } from '@/api'

const { hasRole } = useRoles()
const canProvisional = computed(() => hasRole(['manager','owner']))

// ===== 【1】ref の先行宣言（参照順依存をゼロにする） =====
const memoRef = ref('')
const applyServiceChargeRef = ref(true)
const applyTaxRef = ref(true)
const billTags = ref([])
const selectedTagIds = ref([])
const selectedCustomerId = ref(null)  // 注文作成時の顧客選択
const billCustomersComposable = useBillCustomers()

const props = defineProps({
  modelValue: Boolean,
  bill: { type: Object, required: true },
  serviceRate: { type: Number, default: 0.3 },
  taxRate:    { type: Number, default: 0.1 },
})
const emit = defineEmits(['update:modelValue','saved','updated','closed'])

// ===== 【2】stay 形状を吸収するユーティリティ =====
function getStayCastId(s) {
  return Number(s?.cast?.id ?? s?.cast_id ?? s?.cast ?? null)
}

function isActiveStay(s) {
  return !s?.left_at
}

function activeStays() {
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  return stays.filter(isActiveStay)
}

function recomputeFreeIds() {
  return Array.from(new Set(
    activeStays()
      .filter(s => s.stay_type === 'free')
      .map(getStayCastId)
      .filter(Boolean)
  ))
}

function recomputeHelpIds() {
  return Array.from(new Set(
    activeStays()
      .filter(s => s.stay_type === 'free' && s.is_help === true)
      .map(getStayCastId)
      .filter(Boolean)
  ))
}

// ===== 【5】createBill 後の props.bill 同期は helper にまとめる =====
function applyBillPatchToLocal(patch) {
  if (!patch || !props.bill) return

  // identifiers / flags / times
  if (patch.id != null) props.bill.id = patch.id
  if (patch.opened_at !== undefined) props.bill.opened_at = patch.opened_at
  if (patch.expected_out !== undefined) props.bill.expected_out = patch.expected_out
  if (patch.apply_service_charge !== undefined) props.bill.apply_service_charge = patch.apply_service_charge
  if (patch.apply_tax !== undefined) props.bill.apply_tax = patch.apply_tax

  // money fields (fetchBill / settleBill の反映)
  const moneyKeys = [
    'subtotal', 'service_charge', 'tax',
    'grand_total', 'total',
    'paid_cash', 'paid_card',
    'settled_total'
  ]
  for (const k of moneyKeys) {
    if (patch[k] !== undefined) props.bill[k] = patch[k]
  }

  // discounts / memo / closed
  if (patch.discount_rule !== undefined) props.bill.discount_rule = patch.discount_rule
  if (patch.manual_discounts !== undefined) props.bill.manual_discounts = patch.manual_discounts
  if (patch.memo !== undefined) props.bill.memo = patch.memo
  if (patch.closed_at !== undefined) props.bill.closed_at = patch.closed_at
}


// ===== 【4】visible onMounted 周りの初期化を一本化 =====
const storeSlug = ref('')
const normalizeSlug = s => String(s || '').trim().toLowerCase().replace(/_/g, '-')

async function initOnOpen() {
  pane.value = 'base'
  await refreshStoreSlug()
  try {
    billTags.value = await fetchBillTags({ is_active: true })
  } catch (e) {
    console.warn('[BillModalSP] fetch bill tags failed', e)
    billTags.value = []
  }
  memoRef.value = props.bill?.memo ?? ''
  selectedTagIds.value = props.bill?.tags?.map(t => t.id) || []
  resetPaymentFromProps()
  syncChargeFlagsFromBill()

  ensureServedByDefaultOnOpen()

  // tableId 初期化（open時に1回だけ）
  syncingTableInit.value = true
  const initTid = props.bill?.table?.id ?? props.bill?.table ?? null
  if (initTid != null) ed.tableId.value = Number(initTid)
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

// 毎回取り直す関数
async function refreshStoreSlug() {
  try {
    // X-Store-Id が切り替わっていれば、その店舗の slug が返る
    const { data } = await api.get('billing/stores/me/')
    storeSlug.value = normalizeSlug(data?.slug)
    // ローカル保存も更新（PayPanel外でも使うなら）
    if (storeSlug.value) localStorage.setItem('store_slug', storeSlug.value)
  } catch (e) {
    console.warn('[storeSlug] fetch failed', e)
    // 最低限は localStorage から拾う
    storeSlug.value = normalizeSlug(localStorage.getItem('store_slug') || '')
  }
}

// onMounted は localStorage 復元だけ（API呼び出しなし）
onMounted(async () => {
  const ls = localStorage.getItem('store_slug')
  if (ls) {
    storeSlug.value = normalizeSlug(ls)
  }
})

const visible = computed({
  get: () => props.modelValue,
  set: v  => emit('update:modelValue', v)
})
const pane = ref('base')

// watch(visible) で true なら initOnOpen() を呼ぶ（immediate: false）
watch(visible, async v => {
  if (v) {
    await initOnOpen()
  }
}, { immediate: false })

// Bill 顧客リストを取得（伝票ID が変わったら再取得）
watch(() => props.bill?.id, async (billId) => {
  if (billId && visible.value) {
    await billCustomersComposable.fetchBillCustomers(billId)
    selectedCustomerId.value = null  // 顧客選択をリセット
  }
}, { immediate: true })

// 伝票の store が変わったら取り直す（table.store は数値ID）
watch(() => props.bill?.table?.store, () => {
  if (visible.value) refreshStoreSlug()
})

/* composable */
const ed = useBillEditor(toRef(props,'bill'))

/* 席種は親でローカル管理 */
const seatType = ref('main')
function onSeatTypeChange (v) {
  seatType.value = v || 'main'
}

/* テーブル初期化フラグ：初期化中は同期watchを無効にする */
const syncingTableInit = ref(false)

/* テーブル配列から席種候補を自動生成 */
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

/* マスター解決（配列/結果オブジェクト/表記ゆれ吸収） */
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
  if (!Object.keys(dict).length) console.warn('[masters] empty; check X-Store-Id / endpoint')
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

// テーブル変更の同期：既存はPATCH、新規はローカルだけ更新
watch(() => ed.tableId.value, async (tid, prev) => {
  if (syncingTableInit.value) return

  const nextTid = Number(tid) || null
  if (!nextTid) return

  const cur =
    Number(props.bill?.table?.id) ||
    Number(props.bill?.table) ||
    null

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
    console.error('[BillModalSP] updateBillTable failed', e)
    ed.tableId.value = cur
    alert('テーブルの更新に失敗しました')
  }
})

/* Bill 確保 → 行追加の順に統一 */
async function ensureBillId () {
  if (props.bill?.id) return props.bill.id

  const tableId =
    Number(ed.tableId.value) ||
    Number(props.bill?.table?.id) ||
    Number(props.bill?.table) ||
    Number(props.bill?.table_id_hint) ||
    null

  if (!tableId) { alert('テーブルが未選択です'); throw new Error('no table') }

  const paxPayload =
    Number(props.bill?.pax) ||
    Number(ed.pax?.value) ||
    Number(paxFromItems.value) ||
    0

  // ✅ 確認1: 新規伝票 SET適用
  // ensureBillId() 内では apply_* を ref ではなく props.bill の値から導出
  const b = await createBill({
    table: tableId,
    opened_at: props.bill?.opened_at ?? null,
    expected_out: props.bill?.expected_out ?? null,
    pax: paxPayload,
    apply_service_charge: props.bill?.apply_service_charge !== false,
    apply_tax: props.bill?.apply_tax !== false,
  })

  // applyBillPatchToLocal helper を使用
  applyBillPatchToLocal(b)
  return b.id
}

/* SETの適用（BasicsPanel → 親で行追加） */
async function onApplySet (payload){
  await ensureMasters()
  const billId = await ensureBillId()

  // SET（男女：setMale / setFemale）
  for (const ln of payload.lines.filter(l => l.type==='set')) {
    if (!ln.qty) continue
    let mid
    if (ln.code === 'setMale' || ln.code === 'setFemale') {
      // 旧パターン（男女別マスタ名の表記ゆれ対策）
      mid = getMasterId(
        ln.code,
        ln.code === 'setMale' ? 'setmale'   : 'setfemale',
        ln.code === 'setMale' ? 'set-male'  : 'set-female'
      )
    } else {
      // 新パターン：任意コード（例: DSK_A_set3000）をそのまま解決
      mid = getMasterId(ln.code)
    }
    if (!mid) { console.warn('master not found:', ln.code); continue }
    await addBillItem(billId, { item_master: mid, qty: ln.qty })
  }

  // 深夜（addonNight：人数分）
  for (const ln of payload.lines.filter(l => l.type==='addon')) {
    if (!ln.qty) continue
    const mid = getMasterId(ln.code, 'addonnight', 'night')
    if (!mid) { console.warn('addon master not found:', ln.code); continue }
    await addBillItem(billId, { item_master: mid, qty: ln.qty })
  }

  // ★ 割引は DiscountRule に一本化（行は足さない）
  if (payload.discount_code) {
    await setBillDiscountByCode(billId, payload.discount_code)
  } else {
    await updateBillDiscountRule(billId, null)
  }
  
  // ★ 人数を保存：payload.lines から set 行の qty 合計を算出
  const totalPaxFromPayload = payload.lines
    .filter(l => l.type === 'set')
    .reduce((sum, l) => sum + Number(l.qty || 0), 0)
  if (totalPaxFromPayload > 0) {
    await patchBill(billId, { pax: totalPaxFromPayload })
  }
  
  const fresh = await fetchBill(billId).catch(()=>null)
  if (fresh) {
    // applyBillPatchToLocal で一元管理
    applyBillPatchToLocal(fresh)
    props.bill.items = fresh.items
    props.bill.stays = fresh.stays
    emit('updated', fresh)
  }
}

/* PayPanel からの割引保存 */
async function onSaveDiscount(payload) {
  try {
    const billId = await ensureBillId()
    const body = {}
    if (payload && 'discount_rule' in payload) body.discount_rule = payload.discount_rule
    if (payload && Array.isArray(payload.manual_discounts)) body.manual_discounts = payload.manual_discounts
    await settleBill(billId, body)
    const fresh = await fetchBill(billId).catch(()=>null)
    if (fresh) {
      // applyBillPatchToLocal で一元管理
      applyBillPatchToLocal(fresh)
      props.bill.items = fresh.items
      props.bill.stays = fresh.stays
      emit('updated', fresh)
    }
    // alert削除: 保存済みパネルが視覚的フィードバックを提供
  } catch (e) {
    console.error('[BillModalSP] onSaveDiscount failed', e)
    alert('割引の保存に失敗しました')
  }
}

// ===== 人数状態を引き継ぎ ======
 const maleFromItems = computed(() =>
   (props.bill?.items || []).reduce((s,it) => s + (String(it.code)==='setMale'   ? Number(it.qty||0) : 0), 0)
 )
 const femaleFromItems = computed(() =>
   (props.bill?.items || []).reduce((s,it) => s + (String(it.code)==='setFemale' ? Number(it.qty||0) : 0), 0)
 )
 const paxFromItems = computed(() => maleFromItems.value + femaleFromItems.value)

 // ほかで p ax を参照しているなら同期しておくと吉
 watch([maleFromItems, femaleFromItems], ([m,f]) => {
   if (ed?.pax) ed.pax.value = m + f
 }, { immediate:true })

/* 既存 */
const onChooseCourse = async (opt) => {
  const res = await ed.chooseCourse(opt)
  if (res?.updated) emit('updated', props.bill.id)
}
const pageTitle = computed(() => ({ base:'基本', casts:'キャスト', order:'注文', prov:'仮会計', pay:'会計' }[pane.value] || ''))
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
  // 現在ついてるキャストのみを選択肢にする
  return currentCastsForPanel.value.map(c => ({
    id: c.id,
    label: c.stage_name || `cast#${c.id}`
  }))
})
const servedByMap = computed(() => { const map = {}; for (const c of servedByOptions.value || []) map[String(c.id)] = c.label; return map })

/* 提供者IDを常に数値/Nullに正規化する */
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

// v-model 用に型を矯正して OrderPanel へ渡す
const servedByCastIdModel = computed({
  get: () => normalizeCastId(ed.servedByCastId?.value),
  set: (v) => {
    const n = normalizeCastId(v)
    if (ed.servedByCastId) ed.servedByCastId.value = n
  }
})

// 入ってきた値がオブジェクトのときに即座に補正する（警告防止）
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

watch(() => props.bill?.apply_service_charge, (v) => {
  applyServiceChargeRef.value = v !== false
})
watch(() => props.bill?.apply_tax, (v) => {
  applyTaxRef.value = v !== false
})

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
  try {
    await patchChargeFlags({ apply_service_charge: next })
  } catch (e) {
    console.error('[BillModalSP] failed to update apply_service_charge', e)
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
  try {
    await patchChargeFlags({ apply_tax: next })
  } catch (e) {
    console.error('[BillModalSP] failed to update apply_tax', e)
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
  try {
    await patchBill(props.bill.id, { memo: next })
  } catch (e) {
    console.error('[BillModalSP] failed to update memo', e)
  }
}

async function onSelectedTagIdsChange(v) {
  selectedTagIds.value = v || []
  if (props.bill) props.bill.tags = billTags.value.filter(t => selectedTagIds.value.includes(t.id))

  if (!props.bill?.id) return
  try {
    await patchBill(props.bill.id, { tag_ids: selectedTagIds.value })
  } catch (e) {
    console.error('[BillModalSP] failed to update tag_ids', e)
    // リバート
    selectedTagIds.value = props.bill?.tags?.map(t => t.id) || []
  }
}

/* ========== Pay 周り ========== */
const displayGrandTotal = computed(() => {
  const b = props.bill || {}
  return Number((b.total != null && b.total > 0) ? b.total : (b.grand_total ?? 0))
})
// 延長分：サーバ値が不正な場合に備えてローカルで再計算（空伝票なら0）
const extMinutesView = computed(() => {
  const b = props.bill || {}
  const items = Array.isArray(b.items) ? b.items : []
  if (!items.length) return 0
  
  // デバッグ: 各アイテムのカテゴリコードを出力
  console.log('[extMinutesView] アイテム一覧:')
  items.forEach(it => {
    console.log({
      name: it.name,
      code: it.code,
      item_master: it.item_master,
      category_code: it?.item_master?.category?.code,
      category: it?.category,
      category_code_direct: it?.category_code,
      duration_min: it.duration_min,
      qty: it.qty
    })
  })
  
  let mins = 0
  for (const it of items) {
    const code = String(it?.code || it?.item_master?.code || '').toLowerCase()
    const isExt = code.includes('extension')
    if (!isExt) continue
    const dur = Number(it.duration_min || it?.item_master?.duration_min || 30)
    const qty = Number(it.qty || 0)
    mins += Math.max(0, dur) * Math.max(0, qty)
  }
  
  console.log('[extMinutesView] 延長合計分数:', mins)
  return mins || Number(b.ext_minutes || 0) || 0
})
const payCurrent = computed(() => {
  const b = props.bill || {}
  const sub  = Number(b.subtotal       ?? 0)
  const svc  = Number(b.service_charge ?? 0)
  const tax  = Number(b.tax            ?? 0)
  // 未締め: total=0 のことが多いので grand_total を優先
  const total = Number((b.total != null && b.total > 0) ? b.total
                       : (b.grand_total ?? (sub + svc + tax)))
  return { sub, svc, tax, total }
})
const paidCashRef     = ref(props.bill?.paid_cash ?? 0)
const paidCardRef     = ref(props.bill?.paid_card ?? 0)
const cardBrandRef    = ref(props.bill?.card_brand ?? null)
const settledTotalRef = ref(props.bill?.settled_total ?? (props.bill?.grand_total || 0))
const paidTotal   = computed(() => (Number(paidCashRef.value)||0) + (Number(paidCardRef.value)||0))
const targetTotal = computed(() => Number(settledTotalRef.value) || Number(displayGrandTotal.value) || 0)
const diff        = computed(() => paidTotal.value - targetTotal.value)
const overPay     = computed(() => Math.max(0, diff.value))
const canClose    = computed(() => targetTotal.value > 0 && paidTotal.value >= targetTotal.value)
const payRef = ref(null)

watch(() => props.bill?.memo, v => { memoRef.value = v ?? '' })

// 伝票切替時（ID変化）に支払い入力・メモを初期化
function resetPaymentFromProps() {
  const b = props.bill || {}
  paidCashRef.value     = Number(b.paid_cash ?? 0) || 0
  paidCardRef.value     = Number(b.paid_card ?? 0) || 0
  cardBrandRef.value    = b.card_brand ?? null
  settledTotalRef.value = Number(b.settled_total ?? (b.grand_total || 0)) || 0
  memoRef.value         = b.memo ?? ''
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
    } else {
      emit('updated', props.bill.id)
    }
  }catch(e){ console.error(e); alert('数量を増やせませんでした') }
}
const decItem = async (it) => {
  try{
    console.log('[decItem] called with:', it)
    const newQty = (Number(it.qty)||0) - 1
    console.log('[decItem] newQty:', newQty)
    if (newQty <= 0) {
      // ★ qty が 0 になったら削除確認を表示
      if (!confirm('削除しますか？')) return
      console.log('[decItem] deleting item:', it.id)
      await deleteBillItem(props.bill.id, it.id)
      console.log('[decItem] delete success')
    } else {
      console.log('[decItem] updating qty to:', newQty)
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
    } else {
      emit('updated', props.bill.id)
    }
  }catch(e){ console.error('[decItem] error:', e); alert('数量を減らせませんでした') }
}

const changeServedBy = async ({ item, castId }) => {
  try {
    await patchBillItem(props.bill.id, item.id, { served_by_cast_id: castId })
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
    } else {
      emit('updated', props.bill.id)
    }
  }catch(e){ console.error(e); alert('削除に失敗しました') }
}

const setSettledTotal = (v) => { settledTotalRef.value = Number(v) || 0 }
const setPaidCash     = (v) => { paidCashRef.value     = Number(v) || 0 }
const setPaidCard     = (v) => { paidCardRef.value     = Number(v) || 0 }
function fillRemainderToCard(){
  const need = Math.max(0, targetTotal.value - (Number(paidCashRef.value)||0))
  paidCardRef.value = need
}

// ★ BasicsPanel からの時間更新を受けて patch（即時反映＋裏送信）
function onUpdateTimes({ opened_at, expected_out}){
  // ★ 新規伝票でもローカルに保持して後続 save 時に渡す
  if (opened_at !== undefined)  props.bill.opened_at  = opened_at
  if (expected_out !== undefined) props.bill.expected_out = expected_out

  // 既存伝票は即時 patch
  if (props.bill?.id) {
    enqueue('patchBill', { id: props.bill.id, payload: { opened_at, expected_out }})
    enqueue('reconcile', { id: props.bill.id })
  }
}

// ★ BasicsPanel からの人数更新を受けて patch（即時反映＋裏送信）
function onUpdatePax(newPax) {
  // ★ 新規伝票でもローカルに保持
  if (newPax !== undefined) {
    props.bill.pax = newPax
    ed.pax.value = newPax
  }

  // 既存伝票は即時 patch
  if (props.bill?.id) {
    enqueue('patchBill', { id: props.bill.id, payload: { pax: newPax }})
    enqueue('reconcile', { id: props.bill.id })
  }
}

// ★ PayPanelSP からの割引ルール変更を受けて patch
async function onDiscountRuleChange(ruleId) {
  if (!props.bill?.id) return
  const billId = props.bill.id
  try {
    // 楽観更新
    props.bill.discount_rule = ruleId
    // 即時反映
    await updateBillDiscountRule(billId, ruleId)
    // 伝票を再取得して金額を再計算
    const fresh = await fetchBill(billId).catch(() => null)
    if (fresh) {
      emit('updated', fresh)
    }
  } catch (e) {
    console.error('[BillModalSP] failed to update discount rule', e)
    alert('割引の適用に失敗しました')
  }
}

/* ========== 履歴 ========== */
const historyEvents = computed(() => {
  const b = props.bill || {}
  const out = []

  for (const s of (b.stays || [])) {
    const cid = getStayCastId(s) || 'unknown'
    const name = s?.cast?.stage_name
    const avatar = s?.cast?.avatar_url

    out.push({
      key: `in-${cid}-${s.entered_at}`,
      when: s.entered_at,
      name,
      avatar,
      stayTag: s.stay_type,
      ioTag: 'in',
    })

    if (s.left_at) {
      out.push({
        key: `out-${cid}-${s.left_at}`,
        when: s.left_at,
        name,
        avatar,
        stayTag: s.stay_type,
        ioTag: 'out',
      })
    }
  }

  out.sort((a, b) => new Date(b.when) - new Date(a.when))

  if (import.meta.env.DEV) {
    window.__historyEvents = out
    console.log('[historyEvents] stays:', b.stays)
    console.log('[historyEvents] events:', out)
  }

  return out
})

const closing = ref(false)
const deleting = ref(false)
async function confirmClose(){
  if (closing.value || !props.bill?.id) return
  const ok = window.confirm('本当に会計しますか？')
  if (!ok) return
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

    // ① 楽観反映（UI即更新）
    props.bill.paid_cash     = paidCash
    props.bill.paid_card     = paidCard
    props.bill.card_brand    = cardBrand
    props.bill.settled_total = settled
    props.bill.memo          = memoStr
    props.bill.closed_at     = new Date().toISOString()   // “閉店”を即時表示
    // 可能ならリスト側も同期
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
          // ★ ゴースト消し：UI用に“座ってる人”全員を即退席にする
          stays: (bs.list[i].stays || []).map(s => s.left_at ? s : ({ ...s, left_at: nowISO })),
        }
      }
    }catch{}

    // ② 裏送信（順序安全：patch → close → reconcile）
    // ✅ 確認3: onSetInhouse 後 help_ids から外れる
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

    // ③ 親へ通知（UIはもう閉店表示。ここでモーダルも閉じる）
    emit('saved', { id: billId })
    visible.value = false
    // ★ 会計後は次回 'base' パネルを開く（ゴースト防止の一環）
    pane.value = 'base'
    // visible=false の前に、モーダル内のstaysも退席に（重複ブロックは削除）
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
  // 未保存の新規伝票なら、単純にモーダルを閉じる
  if (!billId) {
    visible.value = false
    pane.value = 'base'
    return
  }
  const ok = window.confirm('この伝票を削除します。よろしいですか？')
  if (!ok) return
  deleting.value = true
  try {
    // 楽観更新：一覧から除外
    try {
      const { useBills } = await import('@/stores/useBills')
      const bs = useBills()
      bs.list = (bs.list || []).filter(b => Number(b.id) !== Number(billId))
    } catch {}

    // 非同期削除（オフライン対応キュー）
    enqueue('deleteBill', { id: billId })
    enqueue('reconcile', { id: billId })

    // 親へ通知してモーダルを閉じる
    emit('saved', { id: billId, deleted: true })
    visible.value = false
    pane.value = 'base'
    alert('伝票を削除しました')
  } catch (e) {
    console.error('[BillModalSP] delete failed', e)
    alert('伝票の削除に失敗しました')
  } finally {
    deleting.value = false
  }
}


// ヘルプ機能追加

// 伝票のstays→CastsPanel向け配列
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

// 注文パネル: 最初のキャストを自動選択
watch(() => currentCastsForPanel.value, (casts) => {
  if (!casts || casts.length === 0) return
  const currentIds = casts.map(c => c.id)
  const currentSelected = ed.servedByCastId?.value
  // 既に有効なキャストが選択されていれば変更しない
  if (currentSelected && currentIds.includes(currentSelected)) return
  // 最初のキャストを自動選択
  if (ed.servedByCastId) ed.servedByCastId.value = casts[0].id
}, { immediate: true })

// 注文パネル: キャスト変更時にpending内のnull cast_idを更新（手順に関わらず担当を保存）
watch(() => ed.servedByCastId?.value, (newCastId) => {
  if (!newCastId || !ed.pending?.value) return
  // pending内のcast_idがnull/undefinedの商品を現在のキャストIDで更新
  ed.pending.value.forEach(item => {
    if (item && item.cast_id == null) {
      item.cast_id = newCastId
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
    // 未乗車なら差し込み（free系だけ想定）
    props.bill.stays = [
      ...stays,
      { cast:{ id:Number(castId), stage_name:`cast#${castId}` },
        stay_type: next.stay_type, is_help: !!next.is_help,
        entered_at: nowISO, left_at: null }
    ]
  }
}

// 楽観→ed.* ラッパー 3つ追加
async function onSetMain(castId){
  // 本指＝nom（ヘルプは必ず解除）
  updateStayLocal(castId, { stay_type:'nom', is_help:false })
  try { await ed.setMain(Number(castId)) } catch {}
}

// 【本指×顧客機能】顧客選択モーダルから確定された本指名
async function onSetMainWithCustomer(payload){
  const { castId, customerId } = payload
  
  // 【調査A】UIイベント確認ログ
  console.log('[BillModalSP] onSetMainWithCustomer 呼び出し:', {
    billId: props.bill?.id,
    castId,
    customerId,
    payload
  })
  
  if (!castId || !customerId) {
    console.warn('[BillModalSP] castId または customerId が不正:', { castId, customerId })
    return
  }

  // ① 楽観的UI更新（赤くする）
  console.log('[BillModalSP] 楽観的UI更新実行')
  updateStayLocal(castId, { stay_type:'nom', is_help:false })
  
  // ★ 重要: ed.mainIds も同期（ed.save() で正しく認識させる）
  if (ed.mainIds && !ed.mainIds.value.includes(Number(castId))) {
    ed.mainIds.value = [...ed.mainIds.value, Number(castId)]
  }
  // freeIds から除外（本指名はフリーではない）
  if (ed.freeIds) {
    ed.freeIds.value = ed.freeIds.value.filter(id => Number(id) !== Number(castId))
  }
  // dohanIds から除外（本指名は同伴ではない）
  if (ed.dohanIds) {
    ed.dohanIds.value = ed.dohanIds.value.filter(id => Number(id) !== Number(castId))
  }

  // ② nominations API を叩く（正しいペイロード形式）
  if (props.bill?.id) {
    const requestPayload = {
      customer_id: Number(customerId),
      cast_ids: [Number(castId)],
    }
    
    console.log('[BillModalSP] POST nominations 送信開始:', {
      url: `/billing/bills/${props.bill.id}/nominations/`,
      payload: requestPayload
    })
    
    try {
      const response = await api.post(`/billing/bills/${props.bill.id}/nominations/`, requestPayload)
      
      // 【調査B】Network結果確認
      console.log('[BillModalSP] POST nominations 成功:', {
        status: response.status,
        data: response.data
      })
      
      // ③【オプション】BasicsPanel の初期選択顧客を更新したい場合
      // ed.selectedCustomerId.value = Number(customerId)
    } catch (e) {
      // 【調査B】エラー詳細確認
      console.error('[BillModalSP] POST nominations 失敗:', {
        status: e.response?.status,
        statusText: e.response?.statusText,
        data: e.response?.data,
        error: e
      })
      alert('本指名の登録に失敗しました')
      // 楽観更新をロールバック
      updateStayLocal(castId, { stay_type:'free', is_help:false })
      // ed.mainIds もロールバック
      if (ed.mainIds) {
        ed.mainIds.value = ed.mainIds.value.filter(id => Number(id) !== Number(castId))
      }
      // freeIds に戻す
      if (ed.freeIds && !ed.freeIds.value.includes(Number(castId))) {
        ed.freeIds.value = [...ed.freeIds.value, Number(castId)]
      }
    }
  } else {
    console.warn('[BillModalSP] bill.id が存在しないため、API呼び出しをスキップ')
  }
}

async function onSetFree(castId){
  // 青：free + is_help=false に即時反映
  updateStayLocal(castId, { stay_type:'free', is_help:false })
  try { await ed.setFree(Number(castId)) } catch {}
}

async function onSetInhouse(castId){
  // UI 楽観：緑にする（ヘルプ解除）
  updateStayLocal(castId, { stay_type:'in', is_help:false })

  try {
    await ed.setInhouse(Number(castId))
  } catch {}

  // ★ 重要: ヘルプIDを再計算してサーバに反映（castId は含まれないはず）
  // 【3】onSetInhouse も同様（castIdを別途concatしない。ローカル反映後の再計算結果を送る）
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

  // 紫：free + is_help=true に即時反映
  updateStayLocal(castId, { stay_type:'free', is_help:true })

  // ✅ 確認2: onSetHelp で例外が出ない
  // 【3】onSetHelp は updateStayLocal→ enqueue(patchBill {free_ids: recomputeFreeIds(), help_ids: recomputeHelpIds()})
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
    // 【3】normalizeHelpBeforeSave も同様（recomputeHelpIds()のみ送る）
    const ids = recomputeHelpIds()
    enqueue('patchBill', { id: props.bill.id, payload: { help_ids: ids } })
    enqueue('reconcile', { id: props.bill.id })
  }
}

const saving = ref(false)
async function handleSave(){
  if (saving.value) return
  
  // 【調査C】保存前の状態確認
  console.log('[BillModalSP] handleSave 開始:', {
    billId: props.bill?.id,
    'stays数': props.bill?.stays?.length,
    'nom stays': props.bill?.stays?.filter(s => s.stay_type === 'nom' && !s.left_at).length
  })
  
  saving.value = true
  try{
    normalizeHelpBeforeSave()
    
    console.log('[BillModalSP] ed.save() 実行前')
    const optimistic = await ed.save()
    
    console.log('[BillModalSP] ed.save() 完了:', optimistic)
    emit('saved', optimistic)
  }finally{
    saving.value = false
  }
}

function handleClose() {
  // 閉じる際も保存時と同等のリロードをトリガー
  emit('saved', props.bill)
  visible.value = false
  pane.value = 'base'
}

</script>

<template>
  <BaseModal v-if="bill" v-model="visible" class="billmodal-sp">
    <template #header>
      <div id="header" class="header-bar">
        <div class="page-title fs-1">{{ pageTitle }}</div>
        <div class="button-area fs-5">
          <button :disabled="deleting" @click="confirmDelete" aria-label="delete"><IconTrash /></button>
          <button :disabled="saving" @click="handleSave" aria-label="save"><IconDeviceFloppy /></button>
          <button @click="handleClose" aria-label="close"><IconX /></button>
        </div>
      </div>
    </template>

    <BasicsPanel
      :bill-id="props.bill?.id"
      v-show="pane==='base'"
      :tables="ed.tables.value || []"
      :table-id="ed.tableId.value"
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
      :tags="billTags"
      :selected-tag-ids="selectedTagIds"
      :history-events="historyEvents"
      :bill-customers-from-parent="(billCustomersComposable.customers.value?.length > 0) ? billCustomersComposable.customers.value : null"
      @update-times="onUpdateTimes"
      @update:seatType="onSeatTypeChange" 
      @update:tableId="v => (ed.tableId.value = v)"
      @update:pax="onUpdatePax"
      @update:applyService="onApplyServiceChange"
      @update:applyTax="onApplyTaxChange"
      @update:memo="onMemoChange"
      @update:selectedTagIds="onSelectedTagIdsChange"
      @chooseCourse="(opt, qty) => onChooseCourse(opt, qty)"
      @clearCustomer="ed.clearCustomer"
      @searchCustomer="ed.searchCustomers"
      @pickCustomer="ed.pickCustomerInline"
      @applySet="onApplySet"
      @save="handleSave"
    />

    <CastsPanel
      v-show="pane==='casts'"
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

  <OrderPanel
    v-show="pane==='order'"
    :cat-options="ed.orderCatOptions.value || []"
    :selected-cat="ed.selectedOrderCat.value"
    :order-masters="ed.orderMasters.value || []"
    v-model:served-by-cast-id="servedByCastIdModel"
    :pending="ed.pending.value"
    :master-name-map="masterNameMap"
    :served-by-map="servedByMap"
    :served-by-options="servedByOptions"
    :master-price-map="masterPriceMap"
    :bill-customers="billCustomersComposable.customers.value || []"
    :selected-customer-id="selectedCustomerId"
    @update:selectedCat="v => (ed.selectedOrderCat.value = v)"
    @update:selectedCustomerId="v => (selectedCustomerId = v)"
    @addPending="(id, qty, castId, customerId) => {
      const q = Math.max(1, Number(qty || 1))
      ed.pending.value.push({
        master_id: Number(id),
        qty: q,
        cast_id: (castId == null || castId === '') ? null : Number(castId),
        customer_id: (customerId == null || customerId === '') ? null : Number(customerId)
      })
    }"
    @removePending="i => ed.pending.value.splice(i,1)"
    @clearPending="() => (ed.pending.value = [])"
    @placeOrder="handleSave"
  />

    <PayPanel
       v-show="pane==='pay'"
       ref="payRef"
       :bill-id="props.bill?.id"
       :bill="props.bill"
       :pane="pane"
       :items="bill.items || []"
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
      v-show="pane==='prov' && canProvisional"
      :key="`prov-${props.bill?.id || 'new'}`"
      :bill="props.bill || {}"
      :ed="ed"
      :service-rate="props.serviceRate"
      :tax-rate="props.taxRate"
    />

    <template #footer>
      <div class="modal-footer p-0" style="border-top:1px #f5f5f5 solid;">
        <div class="w-100 px-2 py-2 pb-safe bg-white">
          <div class="nav nav-pills nav-fill small gap-2 pills-flat">
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='base'}"  @click="pane='base'"><IconFileNeutral /><span>基本</span></button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='casts'}" @click="pane='casts'"><IconUser /><span>キャスト</span></button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='order'}" @click="pane='order'"><IconShoppingCart /><span>注文</span></button>
            <button v-if="canProvisional" type="button" class="nav-link d-flex flex-column" :class="{active: pane==='prov'}" @click="pane='prov'"><IconCalculator /><span>仮</span></button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='pay'}"   @click="pane='pay'"><IconReceiptYen /><span>会計</span></button>
          </div>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped lang="scss">
.pills-flat{
  --bs-nav-pills-link-active-bg: white;
  --bs-nav-pills-link-active-color: #000;
}
.pills-flat .nav-link{ background-color:white; color:#a9a9a9; border-radius:.75rem; }
.pills-flat .nav-link.active{ color:#000; font-weight:700; }
.nav{
 flex-wrap: nowrap;
 button{
  white-space: nowrap;
 }
}
</style>
