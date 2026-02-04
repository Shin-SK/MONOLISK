<!-- BillModalPC.vue -->
<script setup>
import { reactive, ref, watch, computed, onMounted, toRef, unref } from 'vue'
import BaseModal      from '@/components/BaseModal.vue'
import Avatar         from '@/components/Avatar.vue'
import { useCustomers } from '@/stores/useCustomers'
import { useBillCustomers } from '@/composables/useBillCustomers'
import { useBills } from '@/composables/useBills'
import {
  api,
  updateBillTimes,
  updateBillCustomers,
  updateBillTable,
  updateBillCasts,
  toggleBillInhouse,
  addBillItem, deleteBillItem, closeBill,
  fetchBill, patchBillItem, patchBill,
  setBillDiscountByCode,
  setBillDohan,
} from '@/api'
import { useCasts }     from '@/stores/useCasts'
import { useMasters }   from '@/stores/useMasters'
import { useTables }    from '@/stores/useTables'
import dayjs from 'dayjs'
import CastsPanel    from '@/components/panel/CastsPanel.vue'
import CustomerModal from '@/components/CustomerModal.vue'
import BasicsPanel   from '@/components/panel/BasicsPanel.vue'
import CustomerPanel from '@/components/CustomerPanel.vue'
import OrderPanel  from '@/components/panel/OrderPanel.vue'
import PayPanel      from '@/components/panel/PayPanel.vue'
import { enqueue }   from '@/utils/txQueue'

/* ---------------------------------------------------------
 * props / emits
 * --------------------------------------------------------- */
const props = defineProps({
  modelValue  : Boolean,
  bill        : Object,
  serviceRate : { type: Number, default: 0.3 },
  taxRate     : { type: Number, default: 0.1 },
})
const emit  = defineEmits(['update:modelValue','saved','updated','closed'])

/* ---------------------------------------------------------
 * v-model 開閉
 * --------------------------------------------------------- */
const visible = computed({
  get : () => props.modelValue,
  set : v  => emit('update:modelValue', v)
})

/* 共通ユーティリティ */
const asId = v => (typeof v === 'object' && v) ? v.id : v
const catCode    = m => typeof m.category === 'string' ? m.category : m.category?.code
const showInMenu = m => typeof m.category === 'object' ? m.category.show_in_menu : true

/* ---------------------------------------------------------
 * ストア／マスター／テーブル
 * --------------------------------------------------------- */
const casts   = ref([])
const masters = ref([])
const tables  = ref([])
const bill    = toRef(props, 'bill')

const castsStore   = useCasts()
const mastersStore = useMasters()
const tablesStore  = useTables()
const onDutySet    = ref(new Set())

const castKeyword  = ref('')
const customers    = useCustomers()

/* Bill 顧客リスト（注文時の顧客選択用） */
const billCustomersComposable = useBillCustomers()

/* PayPanel 参照（割引明細・メモを取り出す） */
const payRefPc  = ref(null)

/* ---------------------------------------------------------
 * storeSlug：LS → API で補完（PayPanel用）
 * --------------------------------------------------------- */
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

// モーダルを開いた瞬間に取り直す
watch(visible, v => { if (v) refreshStoreSlug() }, { immediate: true })

// 伝票の store が変わったら取り直す（table.store は数値ID）
watch(() => props.bill?.table?.store, () => {
  if (visible.value) refreshStoreSlug()
})

// Bill 顧客リストを取得（伝票ID が変わったら再取得）
watch(() => props.bill?.id, async (billId) => {
  if (billId && visible.value) {
    await billCustomersComposable.fetchBillCustomers(billId)
    selectedCustomerId.value = null  // 顧客選択をリセット
  }
}, { immediate: true })

onMounted(async () => {
  // 1) localStorage 優先
  const ls = localStorage.getItem('store_slug')
  if (ls) {
    storeSlug.value = normalizeSlug(ls)
  } else {
    // 2) API: /billing/stores/me/（X-Store-Id に紐づく現在の店舗）
    try {
      const { data } = await api.get('billing/stores/me/')
      storeSlug.value = normalizeSlug(data?.slug)
      if (storeSlug.value) localStorage.setItem('store_slug', storeSlug.value)
    } catch (e) {
      console.warn('[storeSlug] fetch failed', e)
      storeSlug.value = ''
    }
  }
})

/* ---------------------------------------------------------
 * 初回ロード：キャスト/マスター/テーブル & 今日の出勤
 * --------------------------------------------------------- */
const isNew = computed(() => !props.bill?.id)

onMounted(async () => {
  try {
    const storeId = props.bill?.table?.store ?? ''
    await Promise.all([
      castsStore.fetch(storeId),
      mastersStore.fetch(storeId),
      tablesStore.fetch(storeId),
    ])
    // 今日 IN のキャスト
    const today = dayjs().format('YYYY-MM-DD')
    const { data: todayShifts } = await api.get('billing/cast-shifts/', {
      params: { from: today, to: today, store: storeId }
    })
    onDutySet.value = new Set(
      (todayShifts || [])
        .filter(s => s.clock_in && !s.clock_out)
        .map(s => s.cast.id)
    )
    casts.value   = castsStore.list
    masters.value = mastersStore.list
    tables.value  = tablesStore.list
  } catch (e) {
    console.error('casts/masters/tables fetch failed', e)
  }
})

/* ---------------------------------------------------------
 * 閉じる
 * --------------------------------------------------------- */
function tryClose(){
  const dirty = isNew.value && (
    pending.value.length ||
    mainCastIds.value.length ||
    freeCastIds.value.length ||
    inhouseSet.value.size ||
    (props.bill.customers?.length ?? 0) ||
    form.table_id != null ||
    !!form.expected_out
  )
  if (dirty && !confirm('未保存の内容を破棄します。よろしいですか？')) return
  visible.value = false
}

/* 最新化ヘルパー */
const CLOSE_AFTER_SETTLE = true
async function refetchAndSync(billId = props.bill?.id){
  try{
    const fresh = await fetchBill(billId)
    if (fresh) Object.assign(props.bill, fresh) // ローカル表示も即最新化
    emit('saved', fresh || billId)
  }catch(e){
    console.error('refresh failed', e)
  }
}

/* ---------------------------------------------------------
 * BasicsPanel 連携
 * --------------------------------------------------------- */
const pendingDiscountCode = ref(null)
const seatType = ref(
  props.bill?.table?.seat_type != null ? String(props.bill.table.seat_type) : 'main'
)
watch(() => props.bill?.table?.seat_type, v => {
  if (v != null) seatType.value = String(v)
})
watch(seatType, () => { form.table_id = null })

const applyServiceCharge = ref(props.bill?.apply_service_charge !== false)
const applyTax = ref(props.bill?.apply_tax !== false)
watch(() => props.bill?.apply_service_charge, v => { applyServiceCharge.value = v !== false })
watch(() => props.bill?.apply_tax, v => { applyTax.value = v !== false })

// 【フェーズ1】人数状態を items から計算（BillModalSP.vue と同様）
const maleFromItems = computed(() =>
  (props.bill?.items || []).reduce((s,it) => s + (String(it.code)==='setMale' ? Number(it.qty||0) : 0), 0)
)
const femaleFromItems = computed(() =>
  (props.bill?.items || []).reduce((s,it) => s + (String(it.code)==='setFemale' ? Number(it.qty||0) : 0), 0)
)
const paxFromItems = computed(() => maleFromItems.value + femaleFromItems.value)

async function onApplyServiceChangePc(v) {
  const next = !!v
  const prev = applyServiceCharge.value
  applyServiceCharge.value = next
  if (!props.bill?.id) return
  try {
    const updated = await patchBill(props.bill.id, { apply_service_charge: next })
    if (updated) {
      Object.assign(props.bill, updated)
      emit('updated', updated)
    }
  } catch (e) {
    console.error('[BillModalPC] failed to update apply_service_charge', e)
    applyServiceCharge.value = prev
    if (props.bill) props.bill.apply_service_charge = prev
    alert('サービス料の設定を更新できませんでした')
  }
}

async function onApplyTaxChangePc(v) {
  const next = !!v
  const prev = applyTax.value
  applyTax.value = next
  if (!props.bill?.id) return
  try {
    const updated = await patchBill(props.bill.id, { apply_tax: next })
    if (updated) {
      Object.assign(props.bill, updated)
      emit('updated', updated)
    }
  } catch (e) {
    console.error('[BillModalPC] failed to update apply_tax', e)
    applyTax.value = prev
    if (props.bill) props.bill.apply_tax = prev
    alert('TAXの設定を更新できませんでした')
  }
}

async function onApplySet(payload){
  const lines = Array.isArray(payload?.lines) ? payload.lines : []
  const discountCode = payload?.discount_code || null
  const pax = Number(payload?.pax) || 0
  
  // 【フェーズ1】pax更新がある場合は先にAPI反映
  if (pax > 0 && props.bill?.id) {
    try {
      await patchBill(props.bill.id, { pax })
      if (props.bill) props.bill.pax = pax
      
      // 【フェーズ1】pax更新後に顧客リストを再取得
      await billCustomersComposable.fetchBillCustomers(props.bill.id)
      
      // 【フェーズ5】より詳細なログで切り分け可能にする
      if (import.meta.env.DEV) {
        console.log(`[フェーズ5] pax更新完了 → 顧客再取得:`, {
          billId: props.bill.id,
          '更新後のpax': pax,
          'API応答の顧客数': billCustomersComposable.customers.value?.length || 0,
          '顧客ID一覧': (billCustomersComposable.customers.value || []).map(bc => bc.id),
          'タイムスタンプ': new Date().toISOString()
        })
        
        // 【フェーズ5】期待値チェック
        const expectedCount = pax
        const actualCount = billCustomersComposable.customers.value?.length || 0
        if (expectedCount !== actualCount) {
          console.warn(`[フェーズ5] ⚠️ 顧客数不一致検出:`, {
            '期待値(pax)': expectedCount,
            '実際の顧客数': actualCount,
            '差分': actualCount - expectedCount,
            '問題': actualCount < expectedCount ? 'API側で顧客が作成されていない可能性' : 'pax より多い顧客が存在'
          })
        }
      }
    } catch (e) {
      console.error('[applySet] pax update failed:', e)
      alert('人数の更新に失敗しました')
      return
    }
  }
  
  if (!lines.length && !discountCode) return

  const byCat  = new Map((masters.value || []).map(m => [String(m?.category?.code || ''), m]))
  const byCode = new Map((masters.value || []).map(m => [String(m?.code || ''), m]))

  // 行追加
  for (const ln of lines){
    const qty = Number(ln?.qty) || 0
    if (qty <= 0) continue

    const key = String(ln.code || '')
    const master = byCat.get(key) || byCode.get(key)
    if (!master) { console.warn('[applySet] master not found:', ln); continue }

    if (isNew.value){
      pending.value.push({ master_id: master.id, qty, cast_id: null })
    }else{
      addBillItem(props.bill.id, { item_master: master.id, qty })
        .then(() => emit('updated', props.bill.id))
        .catch(e => { console.error(e); alert('追加に失敗しました') })
    }
  }

  // 割引コード
  if (discountCode) {
    if (isNew.value) {
      pendingDiscountCode.value = String(discountCode)
    } else {
      setBillDiscountByCode(props.bill.id, String(discountCode))
        .then(() => refetchAndSync(props.bill.id))
        .catch(e => { console.error(e); alert('割引の適用に失敗しました') })
    }
  }
}


/* ---------------------------------------------------------
 * CastsPanel
 * --------------------------------------------------------- */

const currentCastsForPanel = computed(() => {
  const b = props.bill || {}
  const actives = (b.stays || []).filter(s => !s.left_at)
  const byId = new Map((casts.value || []).map(c => [Number(c.id), c]))
  return actives.map(s => {
    const id = Number(s.cast?.id)
    const base = byId.get(id) || { id, stage_name: s.cast?.stage_name, avatar_url: null }
    return {
      id,
      stage_name: base.stage_name,
      avatar_url: base.avatar_url,
      stay_type: s.stay_type,                // 'free' | 'in' | 'nom' | 'dohan'
      inhouse : s.stay_type === 'in',
      dohan   : s.stay_type === 'dohan',
      is_help : !!s.is_help,
      role    : s.stay_type === 'nom' ? 'main' : 'free'
    }
  })
})
const onDutyIds = computed(() => Array.from(onDutySet.value))

// ====== CastsPanel イベント: 楽観更新 → API確定 ======
function updateStayLocal(castId, next) {
  const stays = props.bill?.stays || []
  const t = stays.find(s => !s.left_at && Number(s.cast?.id) === Number(castId))
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

function recomputeHelpIds() {
  return Array.from(new Set(
    (props.bill?.stays || [])
      .filter(s => !s.left_at && s.stay_type === 'free' && s.is_help === true)
      .map(s => Number(s.cast?.id))
  ))
}

async function onSetFree(castId){
  updateStayLocal(castId, { stay_type:'free', is_help:false })
  await updateBillCasts(props.bill.id, {
    freeIds:[...new Set([...freeCastIds.value, castId])],
    inIds:[...inhouseSet.value],
    nomIds:[...mainCastIds.value]
  }).catch(()=>{})
  enqueue('patchBill', { id: props.bill.id, payload: { help_ids: recomputeHelpIds() }})
  enqueue('reconcile', { id: props.bill.id })
}

async function onSetInhouse(castId){
  updateStayLocal(castId, { stay_type:'in', is_help:false })
  inhouseSet.value.add(castId)
  await updateBillCasts(props.bill.id, {
    freeIds:[...new Set([...freeCastIds.value, castId])],
    inIds:[...inhouseSet.value],
    nomIds:[...mainCastIds.value]
  }).catch(()=>{})
  enqueue('patchBill', { id: props.bill.id, payload: { help_ids: recomputeHelpIds() }})
  enqueue('reconcile', { id: props.bill.id })
}

async function onSetMain(castId){
  updateStayLocal(castId, { stay_type:'nom', is_help:false })
  if (!mainCastIds.value.includes(castId)) mainCastIds.value.push(castId)
  await updateBillCasts(props.bill.id, {
    freeIds:[...new Set([...freeCastIds.value, castId])],
    inIds:[...inhouseSet.value],
    nomIds:[...mainCastIds.value]
  }).catch(()=>{})
}

async function onSetDohan(castId){
  updateStayLocal(castId, { stay_type:'dohan', is_help:false })
  dohanSet.value.add(castId)
  await setBillDohan(props.bill.id, castId).catch(()=>{})
}

async function onSetHelp(castId){
  // HELP = free + is_help=true
  updateStayLocal(castId, { stay_type:'free', is_help:true })
  await updateBillCasts(props.bill.id, {
    freeIds:[...new Set([...freeCastIds.value, castId])],
    inIds:[...inhouseSet.value],
    nomIds:[...mainCastIds.value]
  }).catch(()=>{})
  enqueue('patchBill', { id: props.bill.id, payload: { help_ids: recomputeHelpIds() }})
  enqueue('reconcile', { id: props.bill.id })
}

async function onRemoveCast(castId){
  const t = (props.bill?.stays || []).find(s => !s.left_at && Number(s.cast?.id) === Number(castId))
  if (t) t.left_at = new Date().toISOString()
  await updateBillCasts(props.bill.id, {
    freeIds: freeCastIds.value.filter(id=>id!==castId),
    inIds  : [...inhouseSet.value].filter(id=>id!==castId),
    nomIds : mainCastIds.value.filter(id=>id!==castId),
  }).catch(()=>{})
  enqueue('patchBill', { id: props.bill.id, payload: { help_ids: recomputeHelpIds() }})
  enqueue('reconcile', { id: props.bill.id })
}


/* ---------------------------------------------------------
 * キャスト系状態
 * --------------------------------------------------------- */
const mainCastIds  = ref([])
const freeCastIds  = ref([])
const inhouseSet   = ref(new Set())
const dohanSet     = ref(new Set())

function toggleMainDohan (cid) {
  const isDohan = dohanSet.value.has(cid)
  if (isDohan) {
    dohanSet.value.delete(cid)
    if (!mainCastIds.value.includes(cid)) mainCastIds.value.push(cid)
  } else {
    mainCastIds.value = mainCastIds.value.filter(x => x !== cid)
    dohanSet.value.add(cid)
  }
}

async function toggleInhouse (cid) {
  if (isNew.value) {
    const nowIn = inhouseSet.value.has(cid)
    if (nowIn) inhouseSet.value.delete(cid); else inhouseSet.value.add(cid)
    if (!freeCastIds.value.includes(cid)) freeCastIds.value.push(cid)
    return
  }
  const nowIn = inhouseSet.value.has(cid)
  try {
    const { stay_type } = await toggleBillInhouse(props.bill.id, { cast_id: cid, inhouse: !nowIn })
    if (stay_type === 'in') {
      inhouseSet.value.add(cid)
      if (!freeCastIds.value.includes(cid)) freeCastIds.value.push(cid)
    } else {
      inhouseSet.value.delete(cid)
      if (!freeCastIds.value.includes(cid)) freeCastIds.value.push(cid)
    }
  } catch (e) { console.error(e); alert('場内フラグの更新に失敗しました') }
}

/* ---------------------------------------------------------
 * 右ペイン：注文/会計タブ
 * --------------------------------------------------------- */
const rightTab   = ref('order')  // 'bill' | 'order'
const isBillTab  = computed(() => rightTab.value === 'bill')
const isOrderTab = computed(() => rightTab.value === 'order')

/* 顧客モーダル */
const activeCustId  = ref(null)
const showCustModal = ref(false)
function openCustModal (id = null) {
  activeCustId.value = asId(id)
  showCustModal.value = true
}
function clearCustomer(target) {
  const id = asId(target)
  props.bill.customers = (props.bill.customers || []).filter(c => asId(c) !== id)
  props.bill.customer_display_name = props.bill.customers.length ? props.bill.customer_display_name : ''
  if (!isNew.value) {
    const ids = (props.bill.customers||[]).map(asId).filter(Boolean)
    enqueue('patchBill', { id: props.bill.id, payload: { customer_ids: ids }})
    enqueue('reconcile', { id: props.bill.id })
  }
}
async function handleCustPicked (cust) {
  const ids = new Set((props.bill.customers ?? []).map(asId))
  ids.add(cust.id)
  props.bill.customers = [...ids]
  props.bill.customer_display_name = cust.alias?.trim() || cust.full_name || `#${cust.id}`
  if (!isNew.value) {
    const list = props.bill.customers.map(asId).filter(Boolean)
    enqueue('patchBill', { id: props.bill.id, payload: { customer_ids: list }})
    enqueue('reconcile', { id: props.bill.id })
  }
  showCustModal.value = false
}
function handleCustSaved(cust) {
  const ids = new Set(props.bill.customers ?? [])
  ids.add(cust.id)
  props.bill.customers = [...ids]
  props.bill.customer_display_name = cust.alias?.trim() || cust.full_name || `#${cust.id}`
  showCustModal.value = false
}

/* ---------------------------------------------------------
 * 注文（カテゴリ/マスター）
 * --------------------------------------------------------- */
const catOptions = computed(() => {
  const codes = [...new Set(
    masters.value
      .filter(m => m.category?.show_in_menu)
      .map(m => m.category.code)
  )]
  return codes.map(code => {
    const m = masters.value.find(v => v.category.code === code)
    return { value: code, label: m?.category.name ?? code }
  })
})
const selectedCat  = ref('drink')
const orderMasters = computed(() => masters.value.filter(m => catCode(m) === selectedCat.value))

/* SP の OrderPanelSP に合わせた変換 */
const servedByCastId = ref(null)
const servedByOptions = computed(() =>
  (currentCasts.value || []).map(c => ({ id: c.id, label: c.stage_name }))
)
const servedByMap = computed(() =>
  Object.fromEntries((currentCasts.value || []).map(c => [String(c.id), c.stage_name]))
)
const masterNameMap = computed(() =>
  Object.fromEntries((masters.value || []).map(m => [String(m.id), m.name]))
)
const masterPriceMap = computed(() =>
  Object.fromEntries((masters.value || []).map(m => [String(m.id), Number(m.price_regular) || 0]))
)
const orderMastersForPanel = computed(() =>
  orderMasters.value.map(m => ({ ...m, price: m.price ?? m.price_regular ?? 0 }))
)

/* 注文ペンディング */
const pending = ref([])   // [{ master_id, qty, cast_id, customer_id }]
const selectedCustomerId = ref(null)  // 注文作成時の顧客選択
// 【フェーズ3】castId と customerId を引数で受け取る
const onAddPending   = (masterId, qty, castId, customerId) => pending.value.push({ 
  master_id: masterId, 
  qty: Number(qty)||0, 
  cast_id: castId ?? servedByCastId.value ?? null,
  customer_id: customerId ?? selectedCustomerId.value ?? null
})
const onRemovePending = (i) => pending.value.splice(i, 1)
const onClearPending  = () => (pending.value = [])
const onPlaceOrder    = async () => { await save() }

async function onChangeServedBy({ item, castId }) {
  if (!props.bill?.id) return
  try {
    await patchBillItem(props.bill.id, item.id, { served_by_cast_id: castId })
    const fresh = await fetchBill(props.bill.id).catch(() => null)
    if (fresh) {
      Object.assign(props.bill, fresh)
      props.bill.items = fresh.items
      props.bill.stays = fresh.stays
      emit('updated', fresh)
    }
  } catch (e) {
    console.error('[onChangeServedBy]', e)
    alert('担当者の変更に失敗しました')
  }
}

/* ---------------------------------------------------------
 * 場内/配席/キャスト表示
 * --------------------------------------------------------- */
const currentCasts = computed(() => {
  const list = []
  for (const id of mainCastIds.value) {
    if (dohanSet.value.has(id)) continue
    const c = casts.value.find(x => x.id === id)
    if (c) list.push({ ...c, role:'main' })
  }
  for (const id of dohanSet.value) {
    const c = casts.value.find(x => x.id === id)
    if (c) list.push({ ...c, role:'dohan' })
  }
  const others = new Set([...freeCastIds.value, ...inhouseSet.value])
  others.forEach(id => {
    if (mainCastIds.value.includes(id) || dohanSet.value.has(id)) return
    const c = casts.value.find(x => x.id === id)
    if (c) list.push({ ...c, role:'free', inhouse: inhouseSet.value.has(id) })
  })
  return list
})
const filteredCasts = computed(() => {
  const base = (casts.value || []).filter(c => onDutySet.value.has(c.id))
  if (!castKeyword.value.trim()) return base
  const kw = castKeyword.value.toLowerCase()
  return base.filter(c => c.stage_name.toLowerCase().includes(kw))
})
function toggleMain(id){
  if (mainCastIds.value.includes(id)){
    mainCastIds.value = mainCastIds.value.filter(x => x !== id)
  }else{
    mainCastIds.value.push(id)
    if (!freeCastIds.value.includes(id)) freeCastIds.value.push(id)
  }
}
function removeCast(id) {
  mainCastIds.value = mainCastIds.value.filter(c => c !== id)
  freeCastIds.value = freeCastIds.value.filter(c => c !== id)
  inhouseSet.value.delete(id)
  dohanSet.value.delete(id)
}

/* 履歴タイムライン */
const historyEvents = computed(() => {
  if (!props.bill) return []
  const events = []
  ;(props.bill.stays || []).forEach(s => {
    events.push({ key: `${s.cast.id}-in-${s.entered_at}`,  when: s.entered_at,  id: s.cast.id, name: s.cast.stage_name, avatar: s.cast.avatar_url, stayTag: s.stay_type, ioTag:'in' })
    if (s.left_at) events.push({ key: `${s.cast.id}-out-${s.left_at}`, when: s.left_at, id: s.cast.id, name: s.cast.stage_name, avatar: s.cast.avatar_url, stayTag: s.stay_type, ioTag:'out' })
  })
  return events.sort((a, b) => new Date(b.when) - new Date(a.when))
})

/* ---------------------------------------------------------
 * ヘッダー情報・時刻編集
 * --------------------------------------------------------- */
const headerInfo = computed(() => {
  const b = props.bill || {}
  const fmt = (dt) => dt ? dayjs(dt).format('HH:mm') : '-'
  return {
    id     : b.id,
    table  : b.table?.number ?? '-',
    start  : fmt(b.opened_at),
    end    : fmt(b.expected_out),
    sets   : b.set_rounds ?? 0,
    extCnt : b.ext_minutes ? Math.ceil(b.ext_minutes / 30) : 0,
  }
})
const editingTime = ref(false)
async function saveTimes () {
  if (isNew.value) { editingTime.value = false; return }
  
  // opened_at は必須（現在値を保持）
  const openedISO   = form.opened_at ? dayjs(form.opened_at).toISOString() : dayjs(props.bill.opened_at).toISOString()
  const expectedISO = form.expected_out ? dayjs(form.expected_out).toISOString() : null
  
  if (openedISO === props.bill.opened_at && expectedISO === props.bill.expected_out) {
    editingTime.value = false; return
  }
  try {
    await updateBillTimes(props.bill.id, { opened_at: openedISO, expected_out: expectedISO })
    props.bill.opened_at = openedISO; props.bill.expected_out = expectedISO
    editingTime.value = false
  } catch (e) { console.error(e); alert('保存に失敗しました') }
}

/* ---------------------------------------------------------
 * 金額・フォーム
 * --------------------------------------------------------- */
const current = computed(() => {
  const b = bill.value || {}
  const sub  = Number(b.subtotal ?? 0)
  const svc  = Number(b.service_charge ?? 0)
  const tax  = Number(b.tax ?? 0)
  const total = Number(b.grand_total ?? (sub + svc + tax))
  return { sub, svc, tax, total }
})

/* 初期化ヘルパー */
const toIdsFromAtoms = (atoms) => {
  // atoms: ['A','B'] | [{id,name}, ...] | undefined
  if (!Array.isArray(atoms)) return []
  // 文字列配列なら ID は取れない → 空配列（サーバから table_atom_ids を採用する前提）
  const first = atoms[0]
  if (typeof first === 'string') return []
  return atoms.map(a => a.id).filter(Boolean)
}

const form = reactive({
  table_id: props.bill?.table?.id ?? props.bill?.table ?? null,
  table_ids: props.bill?.table_atom_ids
    ? [...props.bill.table_atom_ids]                    // 推奨：サーバの ID 配列
    : toIdsFromAtoms(props.bill?.table_atoms || []),    // 互換フォールバック
  opened_at: props.bill?.opened_at
    ? dayjs(props.bill.opened_at).format('YYYY-MM-DDTHH:mm')
    : dayjs().format('YYYY-MM-DDTHH:mm'),
  expected_out: props.bill?.expected_out
    ? dayjs(props.bill.expected_out).format('YYYY-MM-DDTHH:mm')
    : '',
  nominated_casts: [],
  inhouse_casts: [],
  paid_cash: props.bill?.paid_cash ?? 0,
  paid_card: props.bill?.paid_card ?? 0,
  card_brand: props.bill?.card_brand ?? null,
  settled_total: props.bill?.settled_total ?? (props.bill?.grand_total || 0),
})

const memoRef = ref(props.bill?.memo ?? '')
watch(() => props.bill?.memo, v => { memoRef.value = v ?? '' })

/* 差額等 */
const displayGrandTotal = computed(() => bill.value?.grand_total ?? 0)
const paidTotal   = computed(() => (form.paid_cash || 0) + (form.paid_card || 0))
const targetTotal = computed(() => form.settled_total || displayGrandTotal.value)
const diff        = computed(() => paidTotal.value - targetTotal.value)
const overPay     = computed(() => Math.max(0, diff.value))
const canClose    = computed(() => targetTotal.value > 0 && paidTotal.value >= targetTotal.value)
function fillRemainderToCard () {
  const need = Math.max(0, targetTotal.value - (form.paid_cash || 0))
  form.paid_card = need
}

/* ---------------------------------------------------------
 * 会計確定（PayPanel の割引明細を取り込み）
 * --------------------------------------------------------- */
const closing = ref(false)
function handleUpdateDiscountRule(ruleId){
  enqueue('patchBill', { id: props.bill.id, payload: { discount_rule: ruleId }})
  enqueue('reconcile', { id: props.bill.id })
}
async function confirmClose(){
  if (closing.value) return
  closing.value = true
  try{
    const billId   = props.bill.id
    const memoFromPanel = String(memoRef.value || '')
    const disc = payRefPc.value?.getDiscountEntry?.() || { label: null, amount: 0 }
    const memoStr = disc.amount > 0
      ? `${memoFromPanel}\n割引明細: ${disc.label} / 金額: ¥${disc.amount.toLocaleString()}`
      : memoFromPanel
    const settled  = form.settled_total || displayGrandTotal.value
    const paidCash = form.paid_cash || 0
    const paidCard = form.paid_card || 0
    const cardBrand = form.card_brand ?? null
    const rows = payRefPc.value?.getManualDiscounts?.() || []

    // 楽観反映
    Object.assign(props.bill, {
      paid_cash: paidCash, paid_card: paidCard, card_brand: cardBrand,
      settled_total: settled, memo: memoStr,
      closed_at: new Date().toISOString(),
    })

    // 一覧ストアも即時更新（残像を消す）：stays を退席扱いに
    try {
      const { useBills } = await import('@/stores/useBills')
      const bs = useBills()
      const i = bs.list.findIndex(b => Number(b.id) === Number(billId))
      if (i >= 0) {
        const nowISO = new Date().toISOString()
        bs.list[i] = {
          ...bs.list[i],
          paid_cash: paidCash,
          paid_card: paidCard,
          card_brand: cardBrand,
          settled_total: settled,
          memo: memoStr,
          closed_at: nowISO,
          stays: (bs.list[i].stays || []).map(s => s.left_at ? s : ({ ...s, left_at: nowISO })),
        }
      }
    } catch {}

    // 裏送信
   enqueue('patchBill', { id: billId, payload: {
     paid_cash: paidCash,
     paid_card: paidCard,
     card_brand: cardBrand,
     memo: memoStr,
     discount_rule: props.bill?.discount_rule ?? null, // ルールも維持
     manual_discounts: rows,                            // ★ 追加：手入力割引を保存
     settled_total: settled,                            // 差分が出ないよう合わせて送る
   }})
    enqueue('closeBill', { id: billId, payload: { settled_total: settled }})
    enqueue('reconcile', { id: billId })

    emit('saved', { id: billId })
    if (CLOSE_AFTER_SETTLE) visible.value = false
  }catch(e){
    console.error(e)
    alert('会計に失敗しました（オフラインでも後で確定されます）')
  }finally{
    closing.value = false
  }
}

/* ---------------------------------------------------------
 * 注文保存フロー
 * --------------------------------------------------------- */
const { createBill, updateBill } = useBills()
const saving = ref(false)
async function save () {
  if (saving.value) return
  saving.value = true

  const wasNew = isNew.value
  let billId = props.bill.id

  try {
    // ❶ 新規POST
    if (wasNew) {
      const created = await createBill({
        tableIds: form.table_ids && form.table_ids.length > 0 ? form.table_ids : [],
        opened_at   : form.opened_at ? dayjs(form.opened_at).toISOString() : null,
        expected_out: form.expected_out ? dayjs(form.expected_out).toISOString() : null,
        memo        : String(memoRef.value || ''),
        apply_service_charge: applyServiceCharge.value,
        apply_tax: applyTax.value,
      })
      billId = created.id
      props.bill.id = billId
      props.bill.apply_service_charge = created.apply_service_charge
      props.bill.apply_tax = created.apply_tax
      if ((props.bill.customers?.length ?? 0) > 0) {
        await updateBillCustomers(billId, props.bill.customers)
      }
    } else {
      // 既存：卓/時刻 PATCH
      // Check if table_ids has changed compared to current bill's tables
      const currentTableIds = props.bill?.table_atoms ? props.bill.table_atoms.map(atom => atom.id) : []
      const tableIdsChanged = JSON.stringify(form.table_ids.sort()) !== JSON.stringify(currentTableIds.sort())
      
      if (tableIdsChanged) {
        await updateBill(billId, {
          tableIds: form.table_ids && form.table_ids.length > 0 ? form.table_ids : [],
        })
      }
      await patchBill(billId, {
        opened_at   : form.opened_at    ? dayjs(form.opened_at).toISOString()    : null,
        expected_out: form.expected_out ? dayjs(form.expected_out).toISOString() : null,
        memo        : String(memoRef.value || ''),
        apply_service_charge: applyServiceCharge.value,
        apply_tax: applyTax.value,
      })
    }

    // ❷ キャスト
    if (mainCastIds.value.length || inhouseSet.value.size || freeCastIds.value.length) {
      await updateBillCasts(billId, {
        nomIds  : [...mainCastIds.value],
        inIds   : [...inhouseSet.value],
        freeIds : [...freeCastIds.value],
      })
    }

    for (const cid of dohanSet.value) {
      await setBillDohan(billId, cid)
    }

    // ❸ pending 注文
    for (const it of pending.value) {
      const payload = {
        item_master: it.master_id,
        qty: it.qty,
        served_by_cast_id: it.cast_id ?? undefined
      }
      if (it.customer_id) {
        payload.customer_id = it.customer_id
      }
      await addBillItem(billId, payload)
    }
    pending.value = []

    // ❹ 新規時 pending 割引コード適用
    if (pendingDiscountCode.value) {
      try {
        await setBillDiscountByCode(billId, String(pendingDiscountCode.value))
      } catch (e) {
        console.error(e); alert('割引の適用に失敗しました')
      } finally {
        pendingDiscountCode.value = null
      }
    }

    // ❺ 最新化
    await refetchAndSync(billId)
    rightTab.value = 'bill'
  } catch (e) {
    console.error(e)
    alert('保存に失敗しました')
  } finally {
    saving.value = false
  }
}

/* ---------------------------------------------------------
 * 伝票 or stays 変更時の同期・人数引き継ぎ
 * --------------------------------------------------------- */
watch(
  () => [props.bill, props.bill?.stays?.length],
  () => {
    const b = props.bill
    if (!b) return

    form.table_id     = b.table?.id ?? b.table_id_hint ?? null
    form.paid_cash     = b.paid_cash ?? 0
    form.paid_card     = b.paid_card ?? 0
    form.card_brand    = b.card_brand ?? null
    form.settled_total = b.settled_total ?? b.grand_total ?? 0
    if (Array.isArray(b.customers)) b.customers = b.customers.map(asId)

    const active   = (b.stays ?? []).filter(s => !s.left_at)
    const stayNom  = active.filter(s => s.stay_type === 'nom'  ).map(s => s.cast.id)
    const stayFree = active.filter(s => s.stay_type === 'free' ).map(s => s.cast.id)
    const stayIn   = active.filter(s => s.stay_type === 'in'   ).map(s => s.cast.id)
    const stayDhn  = active.filter(s => s.stay_type === 'dohan').map(s => s.cast.id)

    mainCastIds.value  = stayNom
    freeCastIds.value  = [...new Set([...stayFree, ...stayIn])]
    inhouseSet.value   = new Set(stayIn)
    dohanSet.value     = new Set(stayDhn)
  },
  { immediate: true }
)

/* main が変わったら free から除去 */
watch(mainCastIds, list => {
  const filtered = freeCastIds.value.filter(id => !list.includes(id))
  if (filtered.length !== freeCastIds.value.length) {
    freeCastIds.value = filtered
  }
})
watch(freeCastIds, list => {
  const deduped = list.filter(id => !mainCastIds.value.includes(id))
  if (deduped.length !== list.length) {
    freeCastIds.value = deduped
    return
  }
})
</script>


<template>
  <!-- 伝票がまだ無い瞬間は描画しない -->
  <BaseModal
    v-if="props.bill"
    v-model="visible"
  >
    <button
      class="btn-close position-absolute"
      style="margin-left: unset; top:8px; right:8px; z-index: 999999999;"
      @click="tryClose"
    /> <!-- 閉じるボタン -->
    <div class="p-2 row flex-fill align-items-stretch billmodal-pc h-100 overflow-hidden" >

      <div class="d-flex col-4 min-h-0"><!-- 左ペイン -->
        <div class="outer flex-fill">
            <div class="menu d-md-none">
              <div class="nav nav-pills nav-fill small gap-2">
                <button type="button" class="nav-link" :class="{active: pane==='base'}"    @click="pane='base'">基本</button>
                <button type="button" class="nav-link" :class="{active: pane==='customer'}" @click="pane='customer'">顧客</button>
              </div>
            </div>
            <div class="d-flex justify-content-between flex-md-column flex-row flex-fill">

            <!-- ▼ パネル群（PCは常時 / SPはpaneで出し分け） -->
            <BasicsPanel
              :bill-id="bill?.id"
              :active-pane="pane"
              :tables="tables"
              :table-id="form.table_id"
              :table-ids="form.table_ids"
              :pax="paxFromItems"
              :male="maleFromItems"
              :female="femaleFromItems"
              :course-options="courseOptions"
              :apply-service="applyServiceCharge"
              :apply-tax="applyTax"

              v-model:seatType="seatType"

              @update:tableId="v => (form.table_id = v)"
              @update:tableIds="v => (form.table_ids = v)"
              @update:applyService="onApplyServiceChangePc"
              @update:applyTax="onApplyTaxChangePc"
              @chooseCourse="(opt, qty) => chooseCourse(opt, qty)"
              @jumpToBill="rightTab = 'bill'"
              @applySet="onApplySet"
              @save="save"
            />
          </div>
        </div>
      </div>

      <div class="outer d-flex flex-column gap-4 col-4"><!-- 真ん中 -->
        <CastsPanel
          :current-casts="currentCastsForPanel"
          :bench-casts="casts"
          :on-duty-ids="onDutyIds"
          :keyword="castKeyword"
          @update:keyword="v => (castKeyword.value = v)"
          @setFree="onSetFree"
          @setInhouse="onSetInhouse"
          @setDohan="onSetDohan"
          @setMain="onSetMain"
          @setHelp="onSetHelp"
          @removeCast="onRemoveCast"
          @save="save"
        />
      </div>

      <div class="outer d-flex flex-column position-relative col-4"><!-- 右ペイン -->
        <!-- タブ -->
        <div class="tab nav nav-pills g-1 mb-5 row w-50" role="tablist" aria-label="右ペイン切替">
          <button
            type="button"
            class="nav-link col d-flex align-items-center gap-2"
            :class="{ active: isOrderTab }"
            role="tab"
            :aria-selected="isOrderTab"
            @click="rightTab='order'"
          ><IconShoppingCart />注文</button>
          <button
            type="button"
            class="nav-link col d-flex align-items-center gap-2"
            :class="{ active: isBillTab }"
            role="tab"
            :aria-selected="isBillTab"
            @click="rightTab='bill'"
          ><IconReceiptYen />会計</button>
        </div>
        <div class="order-panel-pc" v-show="isOrderTab">
            <OrderPanelSP
              :cat-options="catOptions"
              :selected-cat="selectedCat"
              :order-masters="orderMastersForPanel"
              :served-by-options="servedByOptions"
              :served-by-cast-id="servedByCastId"
              :pending="pending"
              :master-name-map="masterNameMap"
              :served-by-map="servedByMap"
              :master-price-map="masterPriceMap"
              :bill-customers="billCustomersComposable.customers.value || []"
              :selected-customer-id="selectedCustomerId"
              :readonly="false"
              @update:selectedCat="v => (selectedCat = v)"
              @update:servedByCastId="v => (servedByCastId = v)"
              @update:selectedCustomerId="v => (selectedCustomerId = v)"
              @addPending="onAddPending"
              @removePending="onRemovePending"
              @clearPending="onClearPending"
              @placeOrder="onPlaceOrder"
            />
        </div>

        <div class="summary" v-if="isBillTab">
          <PayPanel
            :bill-id="props.bill?.id"
            :items="props.bill.items || []"
            :master-name-map="masterNameMap"
            :served-by-map="servedByMap"
            :served-by-options="servedByOptions"

            :current="current"
            :display-grand-total="displayGrandTotal"

            :settled-total="form.settled_total"
            :paid-cash="form.paid_cash"
            :paid-card="form.paid_card"
            :card-brand="form.card_brand"
            :bill-opened-at="props.bill.opened_at || ''"

            :diff="diff"
            :over-pay="overPay"
            :can-close="canClose"

            :memo="memoRef"
            :discount-rule-id="props.bill.discount_rule"
            :store-slug="storeSlug"
            :dosukoi-discount-unit="1000"
            ref="payRefPc"

            @update:settledTotal="v => (form.settled_total = v)"
            @update:paidCash="v => (form.paid_cash = v)"
            @update:paidCard="v => (form.paid_card = v)"
            @update:cardBrand="v => (form.card_brand = v)"
            @fillRemainderToCard="fillRemainderToCard"
            @confirmClose="confirmClose"
            @update:discountRule="handleUpdateDiscountRule"

            @incItem="it => enqueue('addBillItem', { id: props.bill.id, item: { item_master: it.item_master, qty: 1 }})"
            @decItem="it => enqueue('addBillItem', { id: props.bill.id, item: { item_master: it.item_master, qty: -1 }})"
            @deleteItem="it => cancelItem(0, it)"
            @changeServedBy="onChangeServedBy"
          />

        </div>
      </div>

    </div>
  </BaseModal>
</template>



<style scoped lang="scss">

.btn-check:checked + .btn, :not(.btn-check) + .btn:active, .btn:first-child:active, .btn.active, .btn.show
{
  border: unset !important;
}

.modal-footer{
  display: none;
}

</style>