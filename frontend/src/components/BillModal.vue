<!-- BillModal.vue -->
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
  fetchBill
} from '@/api'
import { useCasts }     from '@/stores/useCasts'
import { useMasters }   from '@/stores/useMasters'
import { useTables }    from '@/stores/useTables'
import dayjs from 'dayjs'
import CustomerModal from '@/components/CustomerModal.vue'

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
const fmt = (n) => (Number(unref(n)) || 0).toLocaleString()

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
    updateBillCustomers(props.bill.id, props.bill.customers)
      .then(() => { originalCustIds.value = [...props.bill.customers] })
      .catch(e => { console.error(e); alert('顧客更新に失敗しました') })
  }
}
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


/* ---------- 顧客情報を即反映 ---------- */
async function handleCustPicked (cust) {
  const ids = new Set((props.bill.customers ?? []).map(asId))
  ids.add(cust.id)
  props.bill.customers = [...ids]
  props.bill.customer_display_name = cust.alias?.trim() || cust.full_name || `#${cust.id}`

  if (!isNew.value) {
    try {
      await updateBillCustomers(props.bill.id, props.bill.customers)
      originalCustIds.value = [...props.bill.customers]
    } catch (e) { console.error(e); alert('顧客情報の取得に失敗しました') }
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

/* ── 会計処理 ─────────────────────────── */

const displayGrandTotal = computed(() => bill.value?.grand_total ?? 0)

const paidTotal   = computed(() => (form.paid_cash || 0) + (form.paid_card || 0))
const targetTotal = computed(() => form.settled_total || displayGrandTotal.value)
const diff        = computed(() => paidTotal.value - targetTotal.value)
const overPay     = computed(() => Math.max(0, diff.value))
const canClose    = computed(() => targetTotal.value > 0 && paidTotal.value >= targetTotal.value)

function useGrandTotal () { form.settled_total = displayGrandTotal.value }
function fillRemainderToCard () {
  const need = Math.max(0, targetTotal.value - (form.paid_cash || 0))
  form.paid_card = need
}

const diffClass = computed(() => ({
  'text-danger': diff.value !== 0,
  'text-success': diff.value === 0,
}))


const closing = ref(false)
async function confirmClose(){
  if (closing.value) return
  closing.value = true
  try{
    // 支払内訳 → クローズ
    await api.patch(`billing/bills/${props.bill.id}/`, {
      paid_cash: form.paid_cash || 0,
      paid_card: form.paid_card || 0,
    })
    await api.post(`billing/bills/${props.bill.id}/close/`, {
      settled_total: form.settled_total || displayGrandTotal.value,
    })
    // 最新Billを取得して親へ渡す（親側でclose & 再描画）
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('saved', fresh || props.bill.id)
    // 自分でも即閉じる（v-model）
    visible.value = false
  }catch(e){
    console.error(e)
    alert('会計に失敗しました')
  }finally{
    closing.value = false
  }
}



/* --- 会計確定処理 --- */
const settleAmount = ref(null)

async function settleBill () {
	if (!settleAmount.value || settleAmount.value <= 0) return
	try{
		/*  バックエンド側で settled_total と closed_at を確定させる */
		await closeBill(props.bill.id, { settled_total: settleAmount.value })
		emit('saved', props.bill.id)       // 親に再フェッチさせる
	}catch(e){
		console.error('settle failed', e)
		alert('会計に失敗しました')
	}
}

/* ------- draft ------- */
const draftCode = ref('')   // 'set60' など
const pax       = ref(1)    // 人数
const draftMasterId = ref(null)   // 品名
const draftCastId   = ref(null)   // 誰が注文したか（任意）
const draftQty      = ref(1)      // 数量



async function cancelItem(idx, item){
  if(!confirm('この注文をキャンセルしますか？')) return

  try{
    await deleteBillItem(props.bill.id, item.id)   // ← billId も渡す
    props.bill.items.splice(idx, 1)                // UI から即時削除
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


// コース追加（新規は pending へ積むだけ）
async function chooseCourse(opt){
  if (isNew.value) {
    pending.value.push({ master_id: opt.id, qty: pax.value, cast_id: null })
    return
  }
  // 既存は即POST
  const newItem = await addBillItem(props.bill.id, { item_master: opt.id, qty: pax.value })
  props.bill.items.push(newItem)
  emit('updated', props.bill.id)
  if (form.table_id !== props.bill.table?.id) {
    await api.patch(`billing/bills/${props.bill.id}/`, { table_id: form.table_id })
  }
}

/* ------- コース追加ボタン専用 ------- */
function addCourse () {
  if (!draftCode.value){
    alert('セットを選択');
    return;
  }
  chooseCourse(draftCode.value);   // ← 既存ヘルパを再利用
}


/* ------- 注文とか ------- */
function addSingle () {
  if (!draftMasterId.value) { alert('品名を選択'); return }
  if (draftQty.value <= 0)  { alert('数量を入力'); return }

  pending.value.push({
    master_id : draftMasterId.value,
    qty       : draftQty.value,
    cast_id   : draftCastId.value || null
  })

  // リセット
  draftMasterId.value = null
  draftCastId.value   = null
  draftQty.value      = 1
}



const currentCasts = computed(() => {
  // mainCastIds だけ先に並べる
  const list = mainCastIds.value
    .map(id => casts.value.find(c => c.id === id))
    .filter(Boolean)
    .map(c => ({ ...c, role:'main' }))

  const others = new Set([...freeCastIds.value, ...inhouseSet.value])
  
  others.forEach(id => {
    // main と重複しないように
    if (!mainCastIds.value.includes(id)) {
      const c = casts.value.find(c => c.id === id)
      if (c) {
        list.push({
          ...c,
          role    : 'free',             // 見た目は free 行
          inhouse : inhouseSet.value.has(id)
        })
      }
    }
  })

  return list
})



/* ------- キャスト絞り込み ------- */
const filteredCasts = computed(() => {
  if (!castKeyword.value.trim()) return casts.value          // 空なら全件
  const kw = castKeyword.value.toLowerCase()
  return casts.value.filter(c => c.stage_name.toLowerCase().includes(kw))
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
  const sub = props.bill.items.reduce(
    (s, it) => s + it.qty *
      (masters.value.find(m => m.id === it.item_master)?.price_regular || it.price || 0),
    0
  )
  const svc = Math.round(sub * props.serviceRate)
  const tax = Math.round((sub + svc) * props.taxRate)
  return { sub, svc, tax, total: sub + svc + tax }
})

/* ------- draft を pending に載せる ---------- */
const pending = ref([])   // [{ master_id, qty }]


/* ------- 仮計算 本計算はバックエンドで ---------- */

const preview = computed(() => {
  const sub = pending.value.reduce(
    (s, i) =>
      s + i.qty * (masters.value.find(m => m.id === i.master_id)?.price_regular || 0),
    0
  )
  const svc = Math.round(sub * props.serviceRate)  // ← 追加した prop を参照
  const tax = Math.round((sub + svc) * props.taxRate)
  return { sub, svc, tax, total: sub + svc + tax }
})

/* ---------- 伝票 or stays 変更時 ---------- */
watch(
  // ❶ 参照・長さだけをトラック（deep にはしない）
  () => [props.bill, props.bill?.stays?.length],
  () => {
    const b = props.bill
    if (!b) return
    form.table_id = b.table?.id ?? b.table_id_hint ?? null

    // 支払いも同期
    form.paid_cash     = b.paid_cash ?? 0
    form.paid_card     = b.paid_card ?? 0
    form.settled_total = b.settled_total ?? b.grand_total ?? 0

    /* ── customers を ID 配列へ統一 ── */
    if (Array.isArray(b.customers)) b.customers = b.customers.map(asId)

    /* ── 現在アクティブな stays を抽出 ── */
    const active   = (b.stays ?? []).filter(s => !s.left_at)
    const stayNom  = active.filter(s => s.stay_type === 'nom' ).map(s => s.cast.id)
    const stayFree = active.filter(s => s.stay_type === 'free').map(s => s.cast.id)
    const stayIn   = active.filter(s => s.stay_type === 'in'  ).map(s => s.cast.id)

    /* ── reactive 変数へ反映 ── */
    mainCastIds.value  = stayNom
    freeCastIds.value  = [...new Set([...stayFree, ...stayIn])]
    inhouseSet.value   = new Set(stayIn)

    form.table_id         = b.table?.id ?? b.table_id_hint ?? null
    originalCustIds.value = [...(b.customers ?? [])]
  },
  { immediate: true }          // deep を外して再帰ループを回避
)


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

    // ❸ pending 注文
    for (const it of pending.value) {
      await addBillItem(billId, {
        item_master: it.master_id,
        qty: it.qty,
        served_by_cast_id: it.cast_id ?? undefined
      })
    }
    pending.value = []

    // ❹ 最新のBillを単発フェッチしてemit
    const fresh = await fetchBill(billId)   // ← stays/items/合計を含む最新
    emit('saved', fresh)                    // ← idではなく中身を渡す
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
      style="margin-left: unset; top:8px; right:8px;"
      @click="tryClose"
    /> <!-- 閉じるボタン -->
    <div
      class="p-2 d-md-flex d-grid flex-column flex-md-row gap-4 h-100"
    >
    <div class="sidebar-cq d-flex">
      <div class="modal-sidebar outer">
          <div class="menu d-md-none">
            <div class="nav nav-pills nav-fill small gap-2">
              <button type="button" class="nav-link" :class="{active: pane==='base'}"    @click="pane='base'">基本</button>
              <button type="button" class="nav-link" :class="{active: pane==='customer'}" @click="pane='customer'">顧客</button>
            </div>
          </div>
          <div class="d-flex justify-content-between flex-md-column flex-row " :class="{'d-none d-md-block': pane!=='base'}">

            <!-- テーブル番号 -->
            <div class="wrap">
              <div class="title"><IconPinned/>テーブル</div>
              <div class="items">
                <select
                  v-model.number="form.table_id"
                  class="form-select text-end"
                  style="width: 80px;"
                >
                  <option
                    class="text-center"
                    :value="null"
                  >
                    -
                  </option>
                  <option
                    v-for="t in tables"
                    :key="t.id"
                    class="text-center"
                    :value="t.id"
                  >
                    {{ t.number }}
                  </option>
                </select>
              </div>
            </div>

            <!-- 人数 -->
            <div class="wrap">
              <div class="title"><IconUsers/>人数</div>
              <div class="items">
                <select
                  v-model.number="pax"
                  class="form-select text-center"
                  style="width: 80px;"
                >
                  <option
                    v-for="n in 12"
                    :key="n"
                    :value="n"
                  >
                    {{ n }}
                  </option>
                </select>
              </div>
            </div>

            <!-- セット -->
            <div class="wrap">
              <div class="title"><IconHistoryToggle/>セット</div>
              <div class="items">
                <select
                  v-model="draftCode"
                  class="form-select"
                  @change="draftCode && chooseCourse(draftCode)"
                >
                  <option :value="null">- SET -</option>
                  <option
                    v-for="c in courseOptions"
                    :key="c.id"
                    :value="c"
                  >
                    {{ c.label }}
                  </option>
                </select>
              </div>
            </div>
            
          </div>
          <!-- 顧客 -->
          <div class="wrap" :class="{'d-none d-md-block': pane!=='customer'}">
            <div class="title position-relative">
              <IconUserScan/>顧客
              <div
                class="position-absolute top-0 bottom-0 end-0 margin-auto p-1"
                role="button"
                @click="openCustModal()"
                >
                <IconSearch :size="16"/>
              </div><!-- 検索ボタン -->
            
            </div>

              <div class="items">
              <div
              v-if="props.bill.customers?.length"
              class="d-flex flex-wrap gap-2">

              <div
                v-for="cid in props.bill.customers"
                :key="cid">

                <!-- 個別削除 -->
                <IconX
                  :size="12"
                  role="button"
                  class="me-2"
                  @click.stop="clearCustomer(cid)"
                />
                <span
                  @click="openCustModal(cid)"
                  style="cursor:pointer;"
                >
                  {{ customers.getLabel(cid) }}
                </span>


              </div>
              </div><!-- 選択済み顧客 -->

            </div>
          </div>
      </div>
    </div>
      <div class="outer d-flex flex-column gap-4">
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
              <!-- 本指名 -->
              <div
                v-if="c.role==='main'"
                class="btn rounded border-secondary bg-white py-3 px-3 d-flex align-items-center fw-bold"
                role="button"
              >
                <!-- ✕ボタン：単なるアイコンに click を付与 -->
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
                <span class="badge bg-danger text-white ms-1 d-flex align-items-center">
                  本指名
                </span>
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
            <span class="input-group-text">
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
      <div class="outer">
        <!-- ── 単品注文フォーム ───────────────────────── -->
        <div class="mb-3 border-top pt-3">
          <label class="form-label fw-bold">単品注文</label>

          <div
            class="d-grid align-items-stretch gap-2 mb-2"
            style="grid-template-columns: 2fr 3fr 3fr 1fr auto;"
          >
            <!-- 2 カテゴリ -->
            <select
              v-model="selectedCat"
              class="form-select"
            >
              <option
                v-for="o in catOptions"
                :key="o.value"
                :value="o.value"
              >
                {{ o.label }}
              </option>
            </select>

            <!-- 1 注文キャスト -->
            <select
              v-model="draftCastId"
              class="form-select"
            >
              <option :value="null">
                ‑ CAST ‑
              </option>
              <option
                v-for="c in currentCasts"
                :key="c.id"
                :value="c.id"
              >
                {{ c.stage_name }}
              </option>
            </select>

            <!-- 3 品名（選択したカテゴリだけが出る） -->
            <select
              v-model="draftMasterId"
              class="form-select"
            >
              <option :value="null">
                ‑ ITEM ‑
              </option>
              <option
                v-for="m in orderMasters"
                :key="m.id"
                :value="m.id"
              >
                {{ m.name }}
              </option>
            </select>

            <!-- 4 -->
            <select
              v-model.number="draftQty"
              class="form-select text-center"
            >
              <option
                v-for="n in 12"
                :key="n"
                :value="n"
              >
                {{ n }}
              </option>
            </select>
            <!-- <input type="number" min="1"
                class="form-control text-end"
                v-model.number="draftQty"> -->

            <!-- 5 追加ボタン -->
            <button
              class="btn btn-dark text-light"
              @click="addSingle"
            >
              <IconShoppingCartPlus />
            </button>
          </div>
        </div>
        <!-- 🛒 ここが「仮確定」カート ----------------------------- -->
        <ul
          v-if="pending.length"
          class="list-group mb-3"
        >
          <li
            v-for="(it,i) in pending"
            :key="i"
            class="list-group-item d-flex justify-content-between align-items-center"
          >
            <span>
              <!--  masters で検索に変更 -->
              {{ masters.find(m => m.id === it.master_id)?.name }}
              <small class="text-muted ms-2">
                {{ casts.find(c => c.id === it.cast_id)?.stage_name || '‑' }}
              </small>
            </span>

            <span class="d-flex align-items-center gap-2">
              <span class="badge bg-secondary">{{ it.qty }}</span>
              <IconTrash
                class="text-danger"
                role="button"
                @click="pending.splice(i,1)"
              />
            </span>
          </li>
        </ul>

        <!-- ▼pending がある時だけ：追加後の仮計算 ------- -->
        <table
          v-if="pending.length"
          class="table table-sm mb-3 text-end border-top"
        >
          <tbody>
            <tr>
              <th class="text-start">
                小計(仮)
              </th>      <td>{{ preview.sub.toLocaleString() }}</td>
            </tr>
            <tr>
              <th class="text-start">
                サービス料(仮)
              </th><td>{{ preview.svc.toLocaleString() }}</td>
            </tr>
            <tr>
              <th class="text-start">
                消費税(仮)
              </th>    <td>{{ preview.tax.toLocaleString() }}</td>
            </tr>
            <tr class="fw-bold">
              <th class="text-start">
                合計(仮)
              </th>
              <td>{{ preview.total.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>

        <div class="d-flex my-5">
          <button class="btn btn-warning flex-fill" @click="save" :disabled="saving">
            注文
          </button>
        </div>


        <table class="table table-sm table-striped">
          <thead>
            <tr>
              <th /><th>品名</th><th>キャスト</th><th class="text-end">
                Qty
              </th><th class="text-end">
                小計
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(it, idx) in props.bill.items"
              :key="it.id"
            >
              <!-- キャンセル -->
              <td class="text-center">
                <IconX
                  :size="12"
                  class="text-danger"
                  role="button"
                  @click="cancelItem(idx, it)"
                />
              </td>
              <td>{{ it.name }}</td>
              <td>{{ it.served_by_cast?.stage_name || '‑' }}</td>
              <td class="text-end">
                {{ it.qty }}
              </td>
              <td class="text-end">
                {{ it.subtotal.toLocaleString() }}
              </td>
            </tr>
          </tbody>
        </table>

        <!-- ▼いつも出す：現状確定分 -------------------- -->
        <table class="table table-sm mb-3 text-end">
          <tbody>
            <tr>
              <th class="text-start">
                小計
              </th>      <td>{{ current.sub.toLocaleString() }}</td>
            </tr>
            <tr>
              <th class="text-start">
                サービス料
              </th><td>{{ current.svc.toLocaleString() }}</td>
            </tr>
            <tr>
              <th class="text-start">
                消費税
              </th>    <td>{{ current.tax.toLocaleString() }}</td>
            </tr>
            <tr class="fw-bold">
              <th class="text-start">
                合計
              </th>
              <td>{{ current.total.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>

        <!-- BillModal.vue のフッター付近などに追記 -->
        <div class="card mt-3">
          <div class="card-header">会計</div>
          <div class="card-body">
            <div class="row g-2">
              <div class="col-4">
                <label class="form-label">現金</label>
                <input type="number" min="0" class="form-control"
                      v-model.number="form.paid_cash">
              </div>
              <div class="col-4">
                <label class="form-label">カード</label>
                <input type="number" min="0" class="form-control"
                      v-model.number="form.paid_card">
              </div>
              <div class="col-4">
                <label class="form-label">会計金額（上書き可）</label>
                <input type="number" min="0" class="form-control"
                      v-model.number="form.settled_total">
              </div>
            </div>

            <div class="mt-2 small text-muted">
              伝票合計: ¥{{ fmt(displayGrandTotal) }} /
              受領合計: ¥{{ fmt(paidTotal) }} /
              差額: <span :class="diffClass">¥{{ fmt(diff) }}</span>
              <button class="btn btn-sm btn-outline-secondary ms-2"
                      @click="fillRemainderToCard">残額をカードへ</button>
              <button class="btn btn-sm btn-outline-secondary ms-2"
                      @click="useGrandTotal">会計金額＝伝票合計</button>
            </div>

            <div class="mt-3 d-flex gap-2">
              <button class="btn btn-primary"
                      :disabled="closing || !canClose"
                      @click="confirmClose">
                <span v-if="closing" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
                会計確定
              </button>
              <div v-if="overPay" class="text-danger small">※お釣り発生: ¥{{ fmt(overPay) }}</div>
            </div>
          </div>
        </div>

        <!-- <div class="d-flex align-items-center gap-2 mt-4">
          <label class="fw-bold mb-0">会計金額</label>
          <input
            v-model.number="settleAmount"
            type="number"
            class="form-control text-end"
            style="max-width:120px;"
          >
          <button
            class="btn btn-info"
            :disabled="!settleAmount"
            @click="settleBill"
          >
            会計
          </button>
        </div> -->
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



<style>

.btn-check:checked + .btn, :not(.btn-check) + .btn:active, .btn:first-child:active, .btn.active, .btn.show
{
  border: unset !important;
}

</style>