<!-- BillModalPC.vue -->
<script setup>
/* ── 必要最小限のインポート ───────────────────── */
import { reactive, ref, watch, computed, onMounted, toRef, unref } from 'vue'
import BaseModal      from '@/components/BaseModal.vue'
import Avatar      from '@/components/Avatar.vue'
import { useCustomers } from '@/stores/useCustomers'
import {
  api,
  updateBillTimes,
  updateBillCustomers,
  updateBillTable,
  updateBillCasts,
  toggleBillInhouse,
  addBillItem, deleteBillItem, closeBill,
  fetchBill,
  setBillDiscountByCode,
  setBillDohan,
} from '@/api'
import { useCasts }     from '@/stores/useCasts'
import { useMasters }   from '@/stores/useMasters'
import { useTables }    from '@/stores/useTables'
import dayjs from 'dayjs'
import CustomerModal from '@/components/CustomerModal.vue'
import BasicsPanel   from '@/components/panel/BasicsPanel.vue'
import CustomerPanel from '@/components/CustomerPanel.vue'
import OrderPanelSP from '@/components/spPanel/OrderPanelSP.vue'
import PayPanel from '@/components/panel/PayPanel.vue'
import { enqueue } from '@/utils/txQueue'


/* ── props / emit ─────────────────────────────── */
const props = defineProps({
  modelValue  : Boolean,
  bill        : Object,
  serviceRate : { type: Number, default: 0.3 },
  taxRate     : { type: Number, default: 0.1 },
})
const emit  = defineEmits(['update:modelValue','saved','updated','closed'])

/* ── v‑model（開閉） ─────────────────────────── */
const visible = computed({
  get : () => props.modelValue,
  set : v  => emit('update:modelValue', v)
})

// --- 共通ヘルパー
const asId = v => (typeof v === 'object' && v) ? v.id : v

// --- ① 共通ユーティリティ -----------------------------
const catCode      = m => typeof m.category === 'string'
                        ? m.category               // "drink"
                        : m.category?.code         // {code:"drink",…}
const showInMenu   = m => typeof m.category === 'object'
                        ? m.category.show_in_menu  // true / false
                        : true                     // 文字列なら表示OK

/* ── status ─────────────── */
const casts   = ref([])
const masters = ref([])
const tables  = ref([])
const bill = toRef(props, 'bill')
const castsStore   = useCasts()
const onDutySet  = ref(new Set())
const mastersStore = useMasters()
const tablesStore  = useTables()
const castKeyword = ref('')
const customers = useCustomers()


/* ── 初回 ─────────────── */
const isNew = computed(() => !props.bill?.id)

// ×ボタンのハンドラ
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


const CLOSE_AFTER_SETTLE = true; // 会計確定後にモーダルを閉じるなら true（SPと同じに開いたままにするなら false）
async function refetchAndSync(billId = props.bill?.id){
	try{
		const fresh = await fetchBill(billId);
		if (fresh) Object.assign(props.bill, fresh);   // ★ローカル表示も即最新化
		emit('saved', fresh || billId);                // 親にも通知（リスト側再取得など）
	}catch(e){
		console.error('refresh failed', e);
	}
}

/* ── BasicsPanel使えるように ─────────────────────────── */
const pendingDiscountCode = ref(null)
const seatType = ref(
  props.bill?.table?.seat_type != null ? String(props.bill.table.seat_type) : 'main'
)
// 伝票のテーブルが差し替わったら追従
watch(() => props.bill?.table?.seat_type, v => {
  if (v != null) seatType.value = String(v)
})

// 席種が変わったら卓選択をリセット（任意）
watch(seatType, () => { form.table_id = null })

function onApplySet(payload){
  const lines = Array.isArray(payload?.lines) ? payload.lines : []
  const discountCode = payload?.discount_code || null
  if (!lines.length && !discountCode) return

  const byCat  = new Map((masters.value || []).map(m => [String(m?.category?.code || ''), m]))
  const byCode = new Map((masters.value || []).map(m => [String(m?.code || ''), m]))

  // ① ラインを pending or 即時追加
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
        .then(async () => {
          await refreshTotals()
          emit('updated', props.bill.id)
        })
        .catch(e => { console.error(e); alert('追加に失敗しました') })
    }
  }

  // ② 割引コードの適用
  if (discountCode) {
    if (isNew.value) {
      // 新規は保存後に適用するため保留
      pendingDiscountCode.value = String(discountCode)
    } else {
      setBillDiscountByCode(props.bill.id, String(discountCode))
        .then(() => refetchAndSync(props.bill.id))
        .catch(e => { console.error(e); alert('割引の適用に失敗しました') })
    }
  }
}

onMounted(async () => {
  try {
    const storeId = props.bill?.table?.store ?? ''   // ← 無ければ全店
      await Promise.all([
        castsStore.fetch(storeId),
        mastersStore.fetch(storeId),
        tablesStore.fetch(storeId),
      ])
      /* ─ 今日シフト IN のキャスト一覧を取るだけ ───────── */
      const today = dayjs().format('YYYY-MM-DD')
      const { data: todayShifts } = await api.get('billing/cast-shifts/', {
        params: { from: today, to: today, store: storeId }
      })
      onDutySet.value = new Set(
        todayShifts
          .filter(s => s.clock_in && !s.clock_out)   // ← ここがポイント
          .map(s => s.cast.id)
      )
      casts.value   = castsStore.list
      masters.value = mastersStore.list
      tables.value  = tablesStore.list
  } catch (e) {
    console.error('casts fetch failed', e)
  }
})

/* ---------- state ---------- */
const mainCastIds  = ref([])
const freeCastIds  = ref([])
const inhouseSet   = ref(new Set())
const originalCustIds = ref([...(props.bill?.customers ?? [])])
const activeCustId  = ref(null)
const showCustModal = ref(false)
function openCustModal (id = null) {     // ★共通オープナー
  activeCustId.value = asId(id)          // ← 正しい変数名
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
    originalCustIds.value = [...ids]
  }
}

// ------------------------------------------------
// 同伴←→本指名トグル
// ------------------------------------------------
const dohanSet = ref(new Set())


function toggleMainDohan (cid) {
  const isDohan = dohanSet.value.has(cid)
  if (isDohan) {
    // 同伴 → 本指
    dohanSet.value.delete(cid)
    if (!mainCastIds.value.includes(cid)) mainCastIds.value.push(cid)
  } else {
    // 本指/その他 → 同伴（本指からは外す）
    mainCastIds.value = mainCastIds.value.filter(x => x !== cid)
    dohanSet.value.add(cid)
  }
}

function handleUpdateDiscountRule(ruleId){
  // null許可でそのままpatch（キュー経由でも直送でもOK）
  enqueue('patchBill', { id: props.bill.id, payload: { discount_rule: ruleId }})
  enqueue('reconcile', { id: props.bill.id })
  // 最新化
  refetchAndSync(props.bill.id)
}


// ------------------------------------------------
// オーダーパネルをこっちに移植しようぜ
// ------------------------------------------------

// 提供者（今ついてる卓の人だけ＋未指定）
const servedByCastId = ref(null)
const servedByOptions = computed(() =>
  (currentCasts.value || []).map(c => ({ id: c.id, label: c.stage_name }))
)
const servedByMap = computed(() =>
  Object.fromEntries((currentCasts.value || []).map(c => [String(c.id), c.stage_name]))
)

// マスター名・価格マップ（price_regular を SP側の price に合わせる）
const masterNameMap = computed(() =>
  Object.fromEntries((masters.value || []).map(m => [String(m.id), m.name]))
)
const masterPriceMap = computed(() =>
  Object.fromEntries((masters.value || []).map(m => [String(m.id), Number(m.price_regular) || 0]))
)
// PC側の orderMasters（price_regular）→ SP側期待の {price} に寄せる
const orderMastersForPanel = computed(() =>
  orderMasters.value.map(m => ({ ...m, price: m.price ?? m.price_regular ?? 0 }))
)

// パネルのイベントをPCの pending/save に橋渡し
const onAddPending = (masterId, qty) => {
  pending.value.push({
    master_id: masterId,
    qty: Number(qty) || 0,
    cast_id: servedByCastId.value ?? null,
  })
}
const onRemovePending = (i) => pending.value.splice(i, 1)
const onClearPending  = () => (pending.value = [])
const onPlaceOrder    = async () => { await save() }  // ★一連完了まで待つ


/*
 * ▶ 場内トグル
 * ------------------------------------------------
 *  1. API へ POST
 *  2. レスポンス stay_type でローカル更新
 */
async function toggleInhouse (cid) {
  if (isNew.value) {
    const nowIn = inhouseSet.value.has(cid)
    if (nowIn) inhouseSet.value.delete(cid); else inhouseSet.value.add(cid)
    if (!freeCastIds.value.includes(cid)) freeCastIds.value.push(cid)
    return
  }
  // 既存のみAPI
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

/* ---------- タブ ---------- */
const rightTab = ref('bill')  // 'bill' | 'order'
const isBillTab  = computed(() => rightTab.value === 'bill')
const isOrderTab = computed(() => rightTab.value === 'order')

/* ---------- 顧客情報を即反映 ---------- */
async function handleCustPicked (cust) {
  const ids = new Set((props.bill.customers ?? []).map(asId))
  ids.add(cust.id)
  props.bill.customers = [...ids]
  props.bill.customer_display_name = cust.alias?.trim() || cust.full_name || `#${cust.id}`

  if (!isNew.value) {
    const list = props.bill.customers.map(asId).filter(Boolean)
    enqueue('patchBill', { id: props.bill.id, payload: { customer_ids: list }})
    enqueue('reconcile', { id: props.bill.id })
    originalCustIds.value = [...list]
  }
  showCustModal.value = false
}

function handleCustSaved(cust) {          // ★新規作成／編集
   const ids = new Set(props.bill.customers ?? [])
   ids.add(cust.id)
   props.bill.customers = [...ids]
   props.bill.customer_display_name =
       cust.alias?.trim() || cust.full_name || `#${cust.id}`
  showCustModal.value = false
}

/* ---------- オーダー ---------- */

const catOptions = computed(() => {
  // ① show_in_menu==true のマスターだけ → ② カテゴリ code をユニーク抽出
  const codes = [...new Set(
    masters.value
      .filter(m => m.category?.show_in_menu)   // POS メニュー ON
      .map(m => m.category.code)               // 'drink' など
  )]

  // ③ code から対応する name を引く
  return codes.map(code => {
    const master = masters.value.find(m => m.category.code === code)
    return {
      value: code,
      label: master?.category.name ?? code     // name が無ければ code
    }
  })
})


const selectedCat  = ref('drink')

const orderMasters = computed(() =>
  masters.value.filter(m => catCode(m) === selectedCat.value)
)


/* ── フォーム ─────────────────────────── */

const form = reactive({
  // 基本編集
  table_id: props.bill?.table?.id ?? props.bill?.table ?? null,
  opened_at: props.bill?.opened_at
    ? dayjs(props.bill.opened_at).format('YYYY-MM-DDTHH:mm')
    : dayjs().format('YYYY-MM-DDTHH:mm'),
  expected_out: props.bill?.expected_out
    ? dayjs(props.bill.expected_out).format('YYYY-MM-DDTHH:mm')
    : '',
  nominated_casts: [],
  inhouse_casts: [],

  // 支払い（←ここを統合）
  paid_cash: props.bill?.paid_cash ?? 0,
  paid_card: props.bill?.paid_card ?? 0,
  settled_total: props.bill?.settled_total ?? (props.bill?.grand_total || 0),
})

/* ── メモ（SPと同じ運用：保存時に送る） ─────────── */
const memoRef = ref(props.bill?.memo ?? '')
watch(() => props.bill?.memo, v => { memoRef.value = v ?? '' })

/* ── 会計処理 ─────────────────────────── */

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

const closing = ref(false)
async function confirmClose(){
  if (closing.value) return
  closing.value = true
  try{
    const billId   = props.bill.id
    const memoStr  = String(memoRef.value || '')
    const settled  = form.settled_total || displayGrandTotal.value
    const paidCash = form.paid_cash || 0
    const paidCard = form.paid_card || 0

    // ① 楽観反映（UI即時）
    Object.assign(props.bill, {
      paid_cash: paidCash, paid_card: paidCard,
      settled_total: settled, memo: memoStr,
      closed_at: new Date().toISOString(),
    })
    // ② 裏送信（順序: patch → close → reconcile）
    enqueue('patchBill', { id: billId, payload: { paid_cash: paidCash, paid_card: paidCard, memo: memoStr }})
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


async function cancelItem(idx, item){
  if(!confirm('この注文をキャンセルしますか？')) return

  try{
    await deleteBillItem(props.bill.id, item.id)
    enqueue('reconcile', { id: props.bill.id })
    await refetchAndSync(props.bill.id)
  }catch(e){
    console.error('cancel failed', e)
    alert('キャンセルに失敗しました')
  }
}

/* ------- コースとか ------- */

const COURSE_CATS = ['setMale','setVip','setFemale']

const courseOptions = computed(() =>
  COURSE_CATS.map(code => {
    const m = masters.value.find(v => catCode(v) === code)
    return m ? { id: m.id, code: m.code, label: m.name } : null
  }).filter(Boolean)
)


// コース追加
async function chooseCourse(opt, qtyOverride = null){
	const qty = Number(qtyOverride ?? pax.value) || 0
	if (qty <= 0) return
	if (isNew.value) {
		pending.value.push({ master_id: opt.id, qty, cast_id: null })
		return
	}
  // 楽観行追加
  props.bill.items = props.bill.items || []
  props.bill.items.push({ id:`tmp-${Date.now()}`, item_master: opt.id, qty, subtotal: 0 })
  // 卓変更が必要なら裏送信
  const curTid = props.bill.table?.id ?? props.bill.table ?? null
  if (form.table_id !== curTid) {
    enqueue('updateBillTable', { id: props.bill.id, table_id: form.table_id })
  }
  enqueue('addBillItem', { id: props.bill.id, item: { item_master: opt.id, qty }})
  enqueue('reconcile', { id: props.bill.id })
}



const currentCasts = computed(() => {
  const list = []

  // 本指（同伴に含まれているIDは除外：同伴優先）
  for (const id of mainCastIds.value) {
    if (dohanSet.value.has(id)) continue
    const c = casts.value.find(x => x.id === id)
    if (c) list.push({ ...c, role:'main' })
  }

  // 同伴（グレー）
  for (const id of dohanSet.value) {
    const c = casts.value.find(x => x.id === id)
    if (c) list.push({ ...c, role:'dohan' })
  }

  // フリー/場内（main と dohan を除外）
  const others = new Set([...freeCastIds.value, ...inhouseSet.value])
  others.forEach(id => {
    if (mainCastIds.value.includes(id) || dohanSet.value.has(id)) return
    const c = casts.value.find(x => x.id === id)
    if (c) list.push({ ...c, role:'free', inhouse: inhouseSet.value.has(id) })
  })

  return list
})




/* ------- キャスト絞り込み ------- */
const filteredCasts = computed(() => {
  const base = (casts.value || []).filter(c => onDutySet.value.has(c.id)) // ★出勤中だけ
  if (!castKeyword.value.trim()) return base
  const kw = castKeyword.value.toLowerCase()
  return base.filter(c => c.stage_name.toLowerCase().includes(kw))
})


/* ---------- 本指名に変わるやつ ---------- */
function toggleMain(id){
  if (mainCastIds.value.includes(id)){
    // 解除
    mainCastIds.value = mainCastIds.value.filter(x => x !== id)
  }else{
    mainCastIds.value.push(id)
    // free 側に無ければ追加（want both? ⇒今のロジックで除去されても OK）
    if (!freeCastIds.value.includes(id))
      freeCastIds.value.push(id)
  }
}

/* ---------- 履歴のやつ ---------- */
const historyEvents = computed(() => {
  if (!props.bill) return []

  const events = []

  ;(props.bill.stays || []).forEach(s => {
    // IN (= 着席)
    events.push({
      key     : `${s.cast.id}-in-${s.entered_at}`,
      when    : s.entered_at,
      id      : s.cast.id,
      name    : s.cast.stage_name,
      avatar  : s.cast.avatar_url,
      stayTag : s.stay_type,           // nom / in / free
      ioTag   : 'in',                  // この行では入店
    })
    // OUT (= 退席) があれば追加
    if (s.left_at) {
      events.push({
        key     : `${s.cast.id}-out-${s.left_at}`,
        when    : s.left_at,
        id      : s.cast.id,
        name    : s.cast.stage_name,
        avatar  : s.cast.avatar_url,
        stayTag : s.stay_type,
        ioTag   : 'out',
      })
    }
  })

  // 時間昇順で並べ替え
  return events.sort((a, b) => new Date(b.when) - new Date(a.when))
})

/* ---------- ヘッダーに入れる基礎情報 ---------- */
const headerInfo = computed(() => {
  const b = props.bill
  if (!b) return {}

  const fmt = (dt) => dt ? dayjs(dt).format('HH:mm') : '‑'

  return {
    id     : b.id,
    table  : b.table?.number ?? '‑',
    start  : fmt(b.opened_at),
    end    : fmt(b.expected_out),
    sets   : b.set_rounds ?? 0,
    extCnt : b.ext_minutes ? Math.ceil(b.ext_minutes / 30) : 0,
  }
})


/* ---------- time-edit toggle ---------- */
const editingTime = ref(false)

async function saveTimes () {
  const openedISO   = form.opened_at    ? dayjs(form.opened_at).toISOString()    : null
  const expectedISO = form.expected_out ? dayjs(form.expected_out).toISOString() : null
  if (isNew.value) { editingTime.value = false; return }   // ← 新規はサーバ送らない
  if (openedISO === props.bill.opened_at && expectedISO === props.bill.expected_out) {
    editingTime.value = false; return
  }
  try {
    await updateBillTimes(props.bill.id, { opened_at: openedISO, expected_out: expectedISO })
    props.bill.opened_at = openedISO; props.bill.expected_out = expectedISO
    editingTime.value = false
  } catch (e) { console.error(e); alert('保存に失敗しました') }
}




/* ------- 現状（確定済み）計算 ------------------- */
const current = computed(() => {
  const b = bill.value || {}
  // サーバ計算結果をそのまま表示（席種別サービス率・丸め方も一致）
  const sub  = Number(b.subtotal ?? 0)
  const svc  = Number(b.service_charge ?? 0)
  const tax  = Number(b.tax ?? 0)
  const total = Number(b.grand_total ?? (sub + svc + tax))
  return { sub, svc, tax, total }
})
/* ------- draft を pending に載せる ---------- */
const pending = ref([])   // [{ master_id, qty }]


/* ---------- 伝票 or stays 変更時 ---------- */
watch(
  () => [props.bill, props.bill?.stays?.length],
  () => {
    const b = props.bill
    if (!b) return

    form.table_id     = b.table?.id ?? b.table_id_hint ?? null
    form.paid_cash     = b.paid_cash ?? 0
    form.paid_card     = b.paid_card ?? 0
    form.settled_total = b.settled_total ?? b.grand_total ?? 0
    if (Array.isArray(b.customers)) b.customers = b.customers.map(asId)
    originalCustIds.value = [...(b.customers ?? [])]

    const active   = (b.stays ?? []).filter(s => !s.left_at)
    const stayNom  = active.filter(s => s.stay_type === 'nom'  ).map(s => s.cast.id)
    const stayFree = active.filter(s => s.stay_type === 'free' ).map(s => s.cast.id)
    const stayIn   = active.filter(s => s.stay_type === 'in'   ).map(s => s.cast.id)
    const stayDhn  = active.filter(s => s.stay_type === 'dohan').map(s => s.cast.id)

    mainCastIds.value  = stayNom
    freeCastIds.value  = [...new Set([...stayFree, ...stayIn])]
    inhouseSet.value   = new Set(stayIn)
    dohanSet.value     = new Set(stayDhn)         // ★ 同伴の反映
  },
  { immediate: true }
)

/* ---------- 人数引き継ぎ ---------- */

 const maleFromItems = computed(() =>
   (props.bill?.items || []).reduce((s,it) => s + (String(it.code)==='setMale'   ? Number(it.qty||0) : 0), 0)
 )
 const femaleFromItems = computed(() =>
   (props.bill?.items || []).reduce((s,it) => s + (String(it.code)==='setFemale' ? Number(it.qty||0) : 0), 0)
 )
 const paxFromItems = computed(() => maleFromItems.value + femaleFromItems.value)

/* ---------- ウォッチャー ---------- */
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
    freeCastIds.value = deduped      // 変化がある時だけ再代入
    return                           // ここで終われば再トリガは 1 回で済む
  }
})


/* キャストをリストから外すだけの共通関数（JSのみ） */
function removeCast(id) {
  // 本指名だったら解除
  mainCastIds.value = mainCastIds.value.filter(c => c !== id)
  // フリー配列から除外
  freeCastIds.value = freeCastIds.value.filter(c => c !== id)

  // 場内セットからも除外
  inhouseSet.value.delete(id)
  dohanSet.value.delete(id)
}

/* ── 保存ボタン ─────────────────────────────── */
const saving = ref(false)

async function save () {
  if (saving.value) return
  saving.value = true

  const wasNew = isNew.value
  let billId = props.bill.id

  try {
    // ❶ 新規POST（customersは後から）
    if (wasNew) {
      const { data: created } = await api.post('billing/bills/', {
        table_id    : form.table_id ?? null,
        opened_at   : form.opened_at ? dayjs(form.opened_at).toISOString() : null,
        expected_out: form.expected_out ? dayjs(form.expected_out).toISOString() : null,
        memo        : String(memoRef.value || ''),
      })
      billId = created.id
      props.bill.id = billId
      if ((props.bill.customers?.length ?? 0) > 0) {
        await updateBillCustomers(billId, props.bill.customers)
        originalCustIds.value = [...props.bill.customers]
      }
    } else {
      // 既存のみ：卓/時刻のPATCH
      const currentTableId = props.bill.table?.id ?? props.bill.table ?? null
      if (currentTableId === null || form.table_id !== currentTableId) {
        await updateBillTable(billId, form.table_id)
      }
      await api.patch(`billing/bills/${billId}/`, {
        opened_at   : form.opened_at    ? dayjs(form.opened_at).toISOString()    : null,
        expected_out: form.expected_out ? dayjs(form.expected_out).toISOString() : null,
        memo        : String(memoRef.value || ''),
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
      await addBillItem(billId, {
        item_master: it.master_id,
        qty: it.qty,
        served_by_cast_id: it.cast_id ?? undefined
      })
    }
    pending.value = []

    // ❸.5 新規時に pending 割引コードがあれば適用
    if (pendingDiscountCode.value) {
      try {
        await setBillDiscountByCode(billId, String(pendingDiscountCode.value))
      } catch (e) {
        console.error(e); alert('割引の適用に失敗しました')
      } finally {
        pendingDiscountCode.value = null
      }
    }

    // ❹ 最新のBillを単発フェッチしてemit
    await refetchAndSync(billId);           // ★ローカルも親も最新化
    rightTab.value = 'bill';                // ★注文後は会計タブに切り替え（任意）
  } catch (e) {
    console.error(e)
    alert('保存に失敗しました')
  } finally {
    saving.value = false
  }
}

const pane = ref('base')
watch(visible, v => { if (v) pane.value = 'base' })


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
    <div
      class="p-2 row flex-fill align-items-stretch"
    >
    <div class="sidebar-cq d-flex col-3">
      <div class="modal-sidebar outer flex-fill">
          <div class="menu d-md-none">
            <div class="nav nav-pills nav-fill small gap-2">
              <button type="button" class="nav-link" :class="{active: pane==='base'}"    @click="pane='base'">基本</button>
              <button type="button" class="nav-link" :class="{active: pane==='customer'}" @click="pane='customer'">顧客</button>
            </div>
          </div>
          <div class="d-flex justify-content-between flex-md-column flex-row flex-fill">

          <!-- ▼ パネル群（PCは常時 / SPはpaneで出し分け） -->
          <BasicsPanel
            :active-pane="pane"
            :tables="tables"
            :table-id="form.table_id"
            :pax="paxFromItems"
            :male="maleFromItems"
            :female="femaleFromItems"
            :course-options="courseOptions"

            v-model:seatType="seatType"

            @update:tableId="v => (form.table_id = v)"
            @update:pax="v => (pax = v)"
            @chooseCourse="(opt, qty) => chooseCourse(opt, qty)"
            @jumpToBill="rightTab = 'bill'"
            @applySet="onApplySet"
            @save="save"
          />

          <CustomerPanel
            :active-pane="pane"
            :customer-ids="props.bill.customers || []"
            :get-label="customers.getLabel"
            :open="openCustModal"
            :clear="clearCustomer"
          />
        </div>
      </div>
    </div>
      <div class="outer d-flex flex-column gap-4 col-5">
        <div class="box">
          <div class="d-flex flex-wrap gap-3 align-items-center">
              <!-- ▼ 表示モード -->
              <template v-if="!editingTime">
                <div class="d-flex align-items-center gap-2 me-4">
                  <span class="fs-1 fw-bold" style=" line-height: 100%;">
                    {{ headerInfo.start }} – {{ headerInfo.end }}
                  </span>
                  <IconPencil :size="20" role="button" @click="editingTime = true" />
                </div>
              </template>
              

              <!-- ▼ 編集モード -->
              <template v-else>
                <div class="d-flex align-items-center gap-2 me-4">
                  <input type="datetime-local"
                        v-model="form.opened_at"
                        class="form-control form-control-sm w-auto" />
                  ～
                  <input type="datetime-local"
                        v-model="form.expected_out"
                        class="form-control form-control-sm w-auto" />

                  <button @click="saveTimes" class="text-success p-0">
                    <IconCircleDashedCheck />
                  </button>
                  <button @click="editingTime = false" class="text-danger p-0">
                    <IconCircleDashedX  />
                  </button>
                </div>
              </template>

              <div class="d-flex gap-3">
                <div class="d-flex align-items-center gap-1">
                  <IconNotes/> {{ isNew ? '未保存' : props.bill.id }}
                </div>
                
                <div class="d-flex align-items-center gap-1">
                  <IconCoinYen /> {{ current.sub.toLocaleString() }}
                </div>

                <div class="d-flex align-items-center gap-1">
                  <IconUsers />{{ pax }}
                </div>

                <div class="d-flex align-items-center gap-1">
                  <IconRefresh /> {{ headerInfo.extCnt }}
                </div>
              </div>
          </div>

        </div>
        <!-- 現在ついているキャストエリア ------------------------------- -->
        <div class="mb-3">
          <!-- (D) 誰もいない時 -->
          <div
            v-if="!currentCasts.length"
            class="border border‑2 rounded p‑4 text-center text-muted d-flex justify-content-center align-items-center bg-light"
            style="min-height: 100px;"
          >
            キャストを選択してください
          </div>

          <!-- (A,B,C) 一覧 -->
          <div
            v-else
            class="d-flex flex-wrap gap-2 bg-light px-3 py-5 rounded"
          >
            <template
              v-for="c in currentCasts"
              :key="c.id"
            >
<!-- 本指名（クリックで同伴へ） -->
<div
  v-if="c.role==='main'"
  class="btn rounded border-secondary bg-white py-3 px-3 d-flex align-items-center fw-bold"
  role="button"
  @click="toggleMainDohan(c.id)"
>
  <IconX :size="12" class="me-2" role="button" @click.stop="removeCast(c.id)" />
  <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="28" class="me-1" />
  <span>{{ c.stage_name }}</span>
  <span class="badge bg-danger text-white ms-1 d-flex align-items-center">本指名</span>
</div>

<!-- 同伴（クリックで本指へ） -->
<div
  v-else-if="c.role==='dohan'"
  class="btn rounded border-secondary bg-white py-3 px-3 d-flex align-items-center fw-bold"
  role="button"
  @click="toggleMainDohan(c.id)"
>
  <IconX :size="12" class="me-2" role="button" @click.stop="removeCast(c.id)" />
  <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="28" class="me-1" />
  <span>{{ c.stage_name }}</span>
  <span class="badge bg-secondary text-white ms-1 d-flex align-items-center">同伴</span>
</div>

              <!-- フリー -->
              <div
                v-else
                class="btn rounded border-secondary fw-bold bg-white py-3 px-3 d-flex align-items-center gap-1"
                role="button"
                @click="toggleInhouse(c.id)"
              >
                <!-- ✕アイコン -->
                <IconX
                  :size="12"
                  class="me-2"
                  role="button"
                  @click.stop="removeCast(c.id)"
                />
                <Avatar
                  :url="c.avatar_url"
                  :alt="c.stage_name"
                  :size="28"
                  class="me-1"
                />
                <span>{{ c.stage_name }}</span>
                <span
                  class="badge"
                  :class="c.inhouse ? 'bg-success' : 'bg-secondary'"
                >
                  {{ c.inhouse ? '場内' : 'フリー' }}
                </span>
              </div>
            </template>
          </div>
        </div>


        <!-- ▼キャスト選択　一括表示 -->
        <div class="mb-3 cast-select">
          <div class="input-group mb-4">
            <span class="input-group-text border-0">
              <IconSearch />
            </span>
            <input
              v-model="castKeyword"
              type="text"
              class="form-control"
              placeholder="キャスト名で絞り込み"
            >
            <!-- クリアボタン（×）-->
            <button
              v-if="castKeyword"
              class="d-flex align-items-center p-2"
              @click="castKeyword=''"
            >
              <IconX :size="12" />
            </button>
          </div>
          <div class="d-flex flex-wrap gap-2">
            <template
              v-for="c in filteredCasts"
              :key="c.id"
            >
              <!-- free 用チェックボックス -->
              <input
                :id="`cast-${c.id}`"
                v-model="freeCastIds"
                class="btn-check"
                type="checkbox"
                :value="c.id"
              >
              <label  
                class="btn d-flex align-items-center"
                :class="[
                  (freeCastIds.includes(c.id) || mainCastIds.includes(c.id))
                    ? 'bg-secondary-subtle'
                    : 'bg-light',
                  !onDutySet.has(c.id) // ← シフト外なら灰色
                    ? 'text-muted opacity-50'
                    : ''
                ]"
                :for="`cast-${c.id}`"
              >
                <!-- Avatar(共通コンポーネント) -->
                <Avatar
                  :url="c.avatar_url"
                  :alt="c.stage_name"
                  :size="28"
                  class="me-1"
                />
                {{ c.stage_name }}
                <!-- 本指名バッジ -->
                <span
                  class="badge ms-2"
                  :class="mainCastIds.includes(c.id) ? 'bg-danger' : 'bg-secondary'"
                  @click.stop="toggleMain(c.id)"
                >
                  本指名
                </span>
              </label>
            </template>
          </div>
        </div>

        <!--  IN / OUT タイムライン -->
        <div class="history bg-light rounded p-3 mt-auto">
          <h6 class="fw-bold mb-2">
            <IconHistoryToggle class="me-1" />着席履歴
          </h6>

          <!-- 空だった場合 -->
          <p
            v-if="!historyEvents.length"
            class="text-muted mb-0"
          >
            履歴はありません
          </p>

          <!-- タイムライン -->
          <ul
            v-else
            class="list-unstyled mb-0 overflow-auto"
            style="max-height: 160px;"
          >
            <li
              v-for="ev in historyEvents"
              :key="ev.key"
              class="d-flex align-items-center gap-2 mb-1"
            >
              <!-- 時刻 -->
              <small
                class="text-muted"
                style="width:40px;"
              >
                {{ dayjs(ev.when).format('HH:mm') }}
              </small>

              <!-- アバター -->
              <Avatar
                :url="ev.avatar"
                :alt="ev.name"
                :size="24"
                class="me-1"
              />

              <!-- 名前 -->
              <span class="flex-grow-1">{{ ev.name }}</span>

              <!-- 区分 (nom / in / free) -->
              <span
                class="badge text-white me-1"
                :class="{
                  'bg-danger' : ev.stayTag==='nom',
                  'bg-success' : ev.stayTag==='in',
                  'bg-secondary': ev.stayTag==='free'
                }"
              >
                {{ ev.stayTag==='nom' ? '本指名'
                  : ev.stayTag==='in' ? '場内'
                    : 'フリー' }}
              </span>

              <!-- IN / OUT -->
              <span
                class="badge"
                :class="ev.ioTag==='in' ? 'bg-primary' : 'bg-dark'"
              >
                {{ ev.ioTag.toUpperCase() }}
              </span>
            </li>
          </ul>
        </div>



        <button class="btn btn-primary w-100" @click="save" :disabled="saving">
        {{ isNew ? '作成して保存' : '保存' }}
        </button>
      </div>

      <div class="outer col-4 d-flex flex-column position-relative">

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
              :readonly="false"
              @update:selectedCat="v => (selectedCat = v)"
              @update:servedByCastId="v => (servedByCastId = v)"
              @addPending="onAddPending"
              @removePending="onRemovePending"
              @clearPending="onClearPending"
              @placeOrder="onPlaceOrder"
            />
        </div>

        <div class="summary" v-if="isBillTab">
          <PayPanel
            :items="props.bill.items || []"
            :master-name-map="masterNameMap"
            :served-by-map="servedByMap"

            :current="current"
            :display-grand-total="displayGrandTotal"

            :settled-total="form.settled_total"
            :paid-cash="form.paid_cash"
            :paid-card="form.paid_card"
            :bill-opened-at="props.bill.opened_at || ''"

            :diff="diff"
            :over-pay="overPay"
            :can-close="canClose"

            :memo="memoRef"
            :discount-rule-id="props.bill.discount_rule"

            @update:settledTotal="v => (form.settled_total = v)"
            @update:paidCash="v => (form.paid_cash = v)"
            @update:paidCard="v => (form.paid_card = v)"
            @fillRemainderToCard="fillRemainderToCard"
            @confirmClose="confirmClose"
            @update:discountRule="handleUpdateDiscountRule"

            @incItem="it => enqueue('addBillItem', { id: props.bill.id, item: { item_master: it.item_master, qty: 1 }})"
            @decItem="it => enqueue('addBillItem', { id: props.bill.id, item: { item_master: it.item_master, qty: -1 }})"
            @deleteItem="it => cancelItem(0, it)"
          />

        </div>
      </div>
    </div>
  <CustomerModal
    v-model="showCustModal"
    :customer-id="activeCustId"
    @picked="handleCustPicked" 
    @saved="handleCustSaved"
  />
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