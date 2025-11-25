<script setup>
import { computed, ref, toRef, watch, nextTick, watchEffect, onMounted } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import BasicsPanel from '@/components/panel/BasicsPanel.vue'
import CastsPanel  from '@/components/panel/CastsPanel.vue'
import OrderPanel  from '@/components/panel/OrderPanel.vue'
import PayPanel from '@/components/panel/PayPanel.vue'
import useBillEditor from '@/composables/useBillEditor'
import ProvisionalPanelSP from '@/components/spPanel/ProvisionalPanelSP.vue'
import { useRoles } from '@/composables/useRoles'
import { enqueue } from '@/utils/txQueue'
import {
  api, addBillItem, updateBillCustomers, updateBillTable, updateBillCasts,
  fetchBill, deleteBillItem, patchBillItemQty, fetchMasters,
  createBill, patchBill,
  setBillDiscountByCode, updateBillDiscountRule,
 } from '@/api'

const { hasRole } = useRoles()
const canProvisional = computed(() => hasRole(['manager','owner']))

const props = defineProps({
  modelValue: Boolean,
  bill: { type: Object, required: true },
  serviceRate: { type: Number, default: 0.3 },
  taxRate:    { type: Number, default: 0.1 },
})
const emit = defineEmits(['update:modelValue','saved','updated','closed'])


// 店舗ごとにパネル切り替え
// defineProps の後に追加（既存の storeSlug 定義は置き換え）
const storeSlug = ref('')
const normalizeSlug = s => String(s || '').trim().toLowerCase().replace(/_/g, '-')

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

onMounted(async () => {
  // 1) localStorage 優先
  const ls = localStorage.getItem('store_slug')
  if (ls) {
    storeSlug.value = normalizeSlug(ls)
    return
  }
  // 2) API: /billing/stores/me/（X-Store-Id に紐づく現在の店舗）
  try {
    const { data } = await api.get('billing/stores/me/')
    storeSlug.value = normalizeSlug(data?.slug)
    if (storeSlug.value) localStorage.setItem('store_slug', storeSlug.value)
  } catch (e) {
    console.warn('[storeSlug] fetch failed', e)
    storeSlug.value = ''
  }
})

const visible = computed({
  get: () => props.modelValue,
  set: v  => emit('update:modelValue', v)
})
const pane = ref('base')

// モーダルを開いた瞬間にパネルを base にリセット（会計後の再開時対策）
watch(visible, v => {
  if (v) {
    pane.value = 'base'
    refreshStoreSlug()
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

watch(visible, v => {
  if (!v) return
 // bill.table が持っているテーブルIDで ed.tableId を初期化
 const initTid = props.bill?.table?.id ?? props.bill?.table ?? null
 if (initTid != null) ed.tableId.value = Number(initTid)
})

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

 // テーブル変更のサーバ同期（既存Billのみ）
 watch(() => ed.tableId.value, async (tid, prev) => {
   if (!props.bill?.id) return             // 新規は保存時にPOSTで送る
   const cur = props.bill?.table?.id ?? null
   if (Number(tid) && Number(tid) !== Number(cur)) {
     try {
       await updateBillTable(props.bill.id, Number(tid))          // PATCH /bills/:id/
       // ローカルBillにも即反映（UIが空表示にならないように）
       const list = ed.tables.value || []
       props.bill.table = list.find(t => Number(t.id) === Number(tid)) || { id: Number(tid) }
     } catch (e) {
       console.error('[BillModalPC] updateBillTable failed', e)
       // 失敗したらロールバック
       ed.tableId.value = cur
       alert('テーブルの更新に失敗しました')
     }
   }
 })

/* Bill 確保 → 行追加の順に統一 */
async function ensureBillId () {
  if (props.bill?.id) return props.bill.id
  const tableId = props.bill?.table?.id ?? props.bill?.table_id_hint ?? ed.tableId.value ?? null
  if (!tableId) { alert('テーブルが未選択です'); throw new Error('no table') }
  const b = await createBill({ table: tableId })
  props.bill.id = b.id
  return b.id
}

/* SETの適用（BasicsPanel → 親で行追加） */
async function onApplySet (payload){
  await ensureMasters()
  const billId = await ensureBillId()

  // SET（男女：setMale / setFemale）
  for (const ln of payload.lines.filter(l => l.type==='set')) {
    if (!ln.qty) continue
    const mid = getMasterId(
      ln.code,
      ln.code === 'setMale' ? 'setmale'   : 'setfemale',
      ln.code === 'setMale' ? 'set-male'  : 'set-female'
    )
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
  const fresh = await fetchBill(billId).catch(()=>null)
  if (fresh) {
    Object.assign(props.bill, fresh)   // Bill本体
    props.bill.items = fresh.items     // リストは丸ごと
    props.bill.stays = fresh.stays
    emit('updated', fresh)
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
  const out = [], seen = new Set(), cc = Array.isArray(ed.currentCasts.value) ? ed.currentCasts.value : []
  for (const c of cc) { const id = Number(c?.id); if (!Number.isFinite(id)||seen.has(id)) continue; out.push({ id, label: c.stage_name || `cast#${id}` }); seen.add(id) }
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  for (const s of stays) { if (!s || s.left_at) continue; const id = Number(s.cast?.id); if (!Number.isFinite(id)||seen.has(id)) continue; out.push({ id, label: s.cast.stage_name || `cast#${id}` }); seen.add(id) }
  return out
})
const servedByMap = computed(() => { const map = {}; for (const c of servedByOptions.value || []) map[String(c.id)] = c.label; return map })

/* ========== Pay 周り ========== */
const displayGrandTotal = computed(() => {
  const b = props.bill || {}
  return Number((b.total != null && b.total > 0) ? b.total : (b.grand_total ?? 0))
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
const settledTotalRef = ref(props.bill?.settled_total ?? (props.bill?.grand_total || 0))
const paidTotal   = computed(() => (Number(paidCashRef.value)||0) + (Number(paidCardRef.value)||0))
const targetTotal = computed(() => Number(settledTotalRef.value) || Number(displayGrandTotal.value) || 0)
const diff        = computed(() => paidTotal.value - targetTotal.value)
const overPay     = computed(() => Math.max(0, diff.value))
const canClose    = computed(() => targetTotal.value > 0 && paidTotal.value >= targetTotal.value)
const payRef = ref(null)
const memoRef = ref(props.bill?.memo ?? '')
watch(() => props.bill?.memo, v => { memoRef.value = v ?? '' })

watch(visible, v => {
  if (!v) return
  memoRef.value = props.bill?.memo ?? ''
})

const incItem = async (it) => {
  try{
    const newQty = (Number(it.qty)||0) + 1
    await patchBillItemQty(props.bill.id, it.id, newQty)
    it.qty = newQty
    it.subtotal = (masterPriceMap.value[String(it.item_master)] || 0) * newQty
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('updated', fresh || props.bill.id)
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
    emit('updated', fresh || props.bill.id)
  }catch(e){ console.error(e); alert('数量を減らせませんでした') }
}
const removeItem = async (it) => {
  try{
    await deleteBillItem(props.bill.id, it.id)
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('updated', fresh || props.bill.id)
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
function onUpdateTimes({ opened_at, expected_out }){
  if (!props.bill?.id) return
  const id = props.bill.id
  // 楽観更新
  if (opened_at !== undefined)  props.bill.opened_at  = opened_at
  if (expected_out !== undefined) props.bill.expected_out = expected_out
  // 送信キューで確定
  enqueue('patchBill', { id, payload: { opened_at, expected_out }})
  enqueue('reconcile', { id })
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
    out.push({
      key: `in-${s.cast?.id}-${s.entered_at}`,
      when: s.entered_at,
      name: s.cast?.stage_name,
      avatar: s.cast?.avatar_url,
      stayTag: s.stay_type,   // 'free'|'in'|'nom'|'dohan'
      ioTag: 'in',
    })
    if (s.left_at) {
      out.push({
        key: `out-${s.cast?.id}-${s.left_at}`,
        when: s.left_at,
        name: s.cast?.stage_name,
        avatar: s.cast?.avatar_url,
        stayTag: s.stay_type,
        ioTag: 'out',
      })
    }
  }
  // 新しい順に
  out.sort((a,b) => new Date(b.when) - new Date(a.when))
  return out
})

const closing = ref(false)
async function confirmClose(){
  if (closing.value || !props.bill?.id) return
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
    const rows = payRef.value?.getManualDiscounts?.() || []

    // ① 楽観反映（UI即更新）
    props.bill.paid_cash     = paidCash
    props.bill.paid_card     = paidCard
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
          paid_cash: paidCash, paid_card: paidCard, settled_total: settled,
          memo: memoStr,
          closed_at: nowISO,
          // ★ ゴースト消し：UI用に“座ってる人”全員を即退席にする
          stays: (bs.list[i].stays || []).map(s => s.left_at ? s : ({ ...s, left_at: nowISO })),
        }
      }
    }catch{}

    // ② 裏送信（順序安全：patch → close → reconcile）
    // discount_ruleも保存（閉じた伝票でも割引情報を保持）
    // ★ 重要: patchBillを先に実行してdiscount_ruleを確実に保存してからcloseBillを実行
    const discountRuleId = props.bill?.discount_rule ? Number(props.bill.discount_rule) : null
    enqueue('patchBill', { id: billId, payload: {
      paid_cash: paidCash,
      paid_card: paidCard,
      memo: memoStr,
      discount_rule: props.bill?.discount_rule ? Number(props.bill.discount_rule) : null,
      manual_discounts: rows,
      settled_total: settled,
      help_ids: helpIdsArr.value,
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
  }catch(e){
    console.error(e)
    alert('会計に失敗しました（オフラインでも後で確定されます）')
  }finally{
    closing.value = false
  }
}


// ヘルプ機能追加

// ヘルプID（伝票閉じたときに送る）
const helpIdsArr = computed(() =>
  (props.bill?.stays || [])
    .filter(s => !s.left_at && s.stay_type === 'free' && s.is_help === true)
    .map(s => Number(s.cast?.id))
)

// 伝票のstays→CastsPanel向け配列
const currentCastsForPanel = computed(() => {
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  const actives = stays.filter(s => !s.left_at)
  const byId = new Map((ed.currentCasts?.value || []).map(c => [Number(c.id), c]))
  return actives.map(s => {
    const id = Number(s.cast?.id)
    const base = byId.get(id) || { id, stage_name: s.cast?.stage_name, avatar_url: null }
    return {
      id,
      stage_name: base.stage_name,
      avatar_url: base.avatar_url,
      stay_type: s.stay_type,
      inhouse: s.stay_type === 'in',
      dohan:   s.stay_type === 'dohan',
      is_honshimei: s.stay_type === 'nom',
      is_help: !!s.is_help,
    }
  })
})


function updateStayLocal(castId, next) {
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  const t = stays.find(s => !s.left_at && Number(s.cast?.id) === Number(castId))
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

async function onSetFree(castId){
  // 青：free + is_help=false に即時反映
  updateStayLocal(castId, { stay_type:'free', is_help:false })
  try { await ed.setFree(Number(castId)) } catch {}
}

function recomputeHelpIds() {
  return Array.from(
    new Set(
      (props.bill?.stays || [])
        .filter(s => !s.left_at && s.stay_type === 'free' && s.is_help === true)
        .map(s => Number(s.cast?.id))
    )
  )
}

async function onSetInhouse(castId){
  // UI 楽観：緑にする（ヘルプ解除）
  updateStayLocal(castId, { stay_type:'in', is_help:false })

  try {
    await ed.setInhouse(Number(castId))
  } catch {}

  // ★ 重要: ヘルプIDを再計算してサーバに反映（castId は含まれないはず）
  const nowHelpIds = recomputeHelpIds()
  enqueue('patchBill', { id: props.bill.id, payload: { help_ids: nowHelpIds } })
  enqueue('reconcile', { id: props.bill.id })
}

async function onSetDohan(castId){
  updateStayLocal(castId, { stay_type:'dohan', is_help:false })
  try { await ed.setDohan(Number(castId)) } catch {}
}

async function onRemoveCast(castId){
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  const t = stays.find(s => !s.left_at && Number(s.cast?.id) === Number(castId))
  if (t) t.left_at = new Date().toISOString()
  try { await ed.removeCast(Number(castId)) } catch {}
}

async function onSetHelp(castId) {
  if (!props.bill?.id) return
  const billId = props.bill.id

  // 紫：free + is_help=true に即時反映
  updateStayLocal(castId, { stay_type:'free', is_help:true })

  // 2 PATCH：free_ids と help_ids を送って確定
  const freeIds = Array.from(new Set(
    (props.bill.stays || [])
      .filter(s => !s.left_at && s.stay_type === 'free')
      .map(s => Number(s.cast.id))
      .concat(Number(castId))
  ))

  enqueue('patchBill', { id: billId, payload: { free_ids: freeIds, help_ids: [Number(castId)] }})
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
    const ids = recomputeHelpIds() // ← free+help だけのID
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

</script>

<template>
  <BaseModal v-if="bill" v-model="visible" class="billmodal-sp">
    <template #header>
      <div id="header" class="header-bar">
        <div class="page-title fs-1">{{ pageTitle }}</div>
        <div class="button-area fs-5">
          <button :disabled="saving" @click="handleSave" aria-label="save"><IconDeviceFloppy /></button>
          <button @click="$emit('update:modelValue', false)" aria-label="close"><IconX /></button>
        </div>
      </div>
    </template>

    <BasicsPanel
      v-show="pane==='base'"
      :tables="ed.tables.value || []"
      :table-id="ed.tableId.value"
      :course-options="ed.courseOptions.value || []"
      :seat-type-options="seatTypeOptions"
      :seat-type="seatType"
      :show-customer="true"
      :customer-name="ed.customerName.value"
      :customer-results="ed.custResults.value"
      :customer-searching="ed.custLoading.value"
      :opened-at="bill.opened_at"
      :expected-out="bill.expected_out"
      :ext-minutes="bill.ext_minutes || 0"
      :set-rounds="bill.set_rounds || 0"
      :pax="paxFromItems"
      :male="maleFromItems"
      :female="femaleFromItems"
      :history-events="historyEvents"
      @update-times="onUpdateTimes"
      @update:seatType="onSeatTypeChange" 
      @update:tableId="v => (ed.tableId.value = v)"
      @update:pax="v => (ed.pax.value = v)"
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
      @update:keyword="v => (ed.castKeyword.value = v)"
      @setFree="onSetFree"
      @setInhouse="onSetInhouse"
      @setDohan="onSetDohan"
      @setMain="onSetMain"
      @removeCast="onRemoveCast"
      @setHelp="onSetHelp"
      @save="handleSave"
    />

    <OrderPanel
      v-show="pane==='order'"
      :cat-options="ed.orderCatOptions.value || []"
      :selected-cat="ed.selectedOrderCat.value"
      :order-masters="ed.orderMasters.value || []"
      :served-by-options="servedByOptions"
      v-model:served-by-cast-id="ed.servedByCastId.value"
      :pending="ed.pending.value"
      :master-name-map="masterNameMap"
      :served-by-map="servedByMap"
      :master-price-map="masterPriceMap"
      @update:selectedCat="v => (ed.selectedOrderCat.value = v)"
      @addPending="(id, qty) => ed.addPending(id, qty)"
      @removePending="i => ed.pending.value.splice(i,1)"
      @clearPending="() => (ed.pending.value = [])"
      @placeOrder="handleSave"
    />

    <PayPanel
       v-show="pane==='pay'"
       ref="payRef"
       :items="bill.items || []"
       :master-name-map="masterNameMap"
       :served-by-map="servedByMap"
       :bill-opened-at="bill.opened_at || ''"
      :current="payCurrent"
      :display-grand-total="displayGrandTotal"
      :memo="props.bill?.memo || ''"
      :settled-total="settledTotalRef"
      :paid-cash="paidCashRef"
      :paid-card="paidCardRef"
      :diff="diff"
      :over-pay="overPay"
      :can-close="canClose"
      :discount-rule-id="props.bill?.discount_rule ? Number(props.bill.discount_rule) : null"
      :store-slug="storeSlug"
      :dosukoi-discount-unit="1000"
      @update:settledTotal="setSettledTotal"
      @update:paidCash="setPaidCash"
      @update:paidCard="setPaidCard"
      @fillRemainderToCard="fillRemainderToCard"
      @confirmClose="confirmClose"
      @incItem="incItem"
      @decItem="decItem"
      @deleteItem="removeItem"
      @update:discountRule="onDiscountRuleChange"
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
