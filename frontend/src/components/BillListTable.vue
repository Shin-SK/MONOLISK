
<!-- ──────────────────────────────────────────────── -->
<!-- BillListTable.vue                               -->
<!-- 伝票＋キャスト DnD 親コンポーネント               -->
<!-- ──────────────────────────────────────────────── -->

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import dayjs from 'dayjs'
import { useBills }    from '@/stores/useBills'
import BillModal       from '@/components/BillModal.vue'
import CastTableDnD    from '@/components/CastTableDnD.vue'
import {
  fetchBill,
  createBill,
  fetchCastShifts,
  updateBillCasts,
} from '@/api'
import { useTables }  from '@/stores/useTables'
import { useCasts }   from '@/stores/useCasts'

// ────────────────────────────────
//  state
// ────────────────────────────────
const billsStore  = useBills()
const tables      = computed(() => tablesStore.list)
const castsAll    = ref([])

const tablesStore = useTables()
const castsStore  = useCasts()

const shiftsToday = ref([])
const currentBill = ref(null)
const showModal   = ref(false)
const todayISO    = dayjs().format('YYYY-MM-DD')

// ────────────────────────────────
//  初期ロード
// ────────────────────────────────
async function loadCastsAndShifts () {
  const [casts, shifts] = await Promise.all([
    // ★ アバター更新反映のため毎回最新取得
    getBillingCasts({ _ts: Date.now() }, { cache: false }),
    fetchCastShifts({ date: todayISO })
  ])
  castsAll.value    = Array.isArray(casts) ? casts : []
  shiftsToday.value = Array.isArray(shifts) ? shifts : []
}

onMounted(async () => {                                   // ★tablesStore.fetch だけ
  await Promise.all([
    billsStore.loadAll(),
    tablesStore.fetch(),          // テーブル一覧
    loadCastsAndShifts(),         // キャスト＋シフト
  ])
  checkDuplicates()
})

function calcRemainMin(bill) {
  if (!bill) return null
  const elapsed = dayjs().diff(dayjs(bill.opened_at), 'minute')
  const limit   = bill.round_min || 60           // 1set=60分等
  return Math.max(limit - elapsed, 0)
}

// ── 追記 ─────────────────────────────
const CLICK_TOL = 8;                 // 8px以上動いたらドラッグ扱い
const press = ref(null);             // { id, x, y, moved }

function onPD(t, e) {
  press.value = { id: t.id, x: e.clientX, y: e.clientY, moved: false }
}
function onPM(e) {
  if (!press.value) return
  if (Math.abs(e.clientX - press.value.x) > CLICK_TOL ||
      Math.abs(e.clientY - press.value.y) > CLICK_TOL) {
    press.value.moved = true
  }
}
function onPU(t) {
  if (!press.value) return
  const moved = press.value.moved
  press.value = null
  if (!moved) openModal(t)          // ★シングルで開く（PC/スマホ共通）
}
function onPC() { press.value = null }
// ────────────────────────────────────


// ────────────────────────────────
//  周期リロード（白フラ防止版）
//   - 一覧は store 側で差分パッチ＆参照維持
//   - モーダル開いてる間は停止、閉じたら即1回だけ更新して再開
// ────────────────────────────────
let shiftTimer = null
async function refreshShifts() {
  shiftsToday.value = await fetchCastShifts({ date: todayISO }, { silent: true })
}
function startPolling() {
  billsStore.startPolling(60_000)
  if (!shiftTimer) shiftTimer = setInterval(refreshShifts, 60_000)
}
function stopPolling() {
  billsStore.stopPolling()
  if (shiftTimer) { clearInterval(shiftTimer); shiftTimer = null }
}

// モーダル表示中は止める → 閉じた瞬間に即同期してから再開
watch(showModal, async (v) => {
  if (v) {
    stopPolling()
  } else {
    await billsStore.loadAll()
    await refreshShifts()
    startPolling()
  }
})

// タブ非表示中は停止（復帰時に即同期）
function onVis() {
  if (document.hidden) stopPolling()
  else { billsStore.loadAll(); refreshShifts(); startPolling() }
}
document.addEventListener('visibilitychange', onVis)

onMounted(() => { startPolling() })
onBeforeUnmount(() => {
  stopPolling()
  document.removeEventListener('visibilitychange', onVis)
})

// ────────────────────────────────
//  Bill マップ
// ────────────────────────────────
const openBillMap = computed(() => {
  const m = new Map()
  billsStore.list.forEach(b => {
    if (!b.closed_at) m.set(b.table?.id || b.table, b)
  })
  return m
})
const getOpenBill = id => openBillMap.value.get(id) ?? null

// ────────────────────────────────
//  空きキャスト算出
// ────────────────────────────────
const unassigned = computed(() => {
  const stayIds = new Set(
    billsStore.list.flatMap(b => (b.stays||[])
      .filter(s => !s.left_at)
      .map(s => Number(s.cast.id)))
  )
  // ★ 出勤中だけ（clock_in あり && clock_out なし）
  const presentIds = new Set(
    shiftsToday.value
      .filter(s => s.clock_in && !s.clock_out)
      .map(s => Number(s.cast.id))
  )
  // ★ アバター最新の castsAll を使う
  return (castsAll.value || [])
    .filter(c => presentIds.has(Number(c.id)) && !stayIds.has(Number(c.id)))
    .map(c => ({
      id    : c.id,
      name  : c.stage_name,
      avatar: c.avatar_url,
      kind  : 'free'
    }))
})

// ────────────────────────────────
//  状態トグル
// ────────────────────────────────
/* ---------- 状態トグル ---------- */
async function handleToggleStay({ castId, billId, nextKind }) {
  /* 1) 対象 Bill をストアから取得 */
  const bill = billsStore.list.find(b => b.id === billId)
  if (!bill) return

  const lists = { freeIds: [], inIds: [], nomIds: [] }
  const push = (id, kind) => {
    if (kind === 'free') lists.freeIds.push(id)
    else if (kind === 'in') lists.inIds.push(id)
    else lists.nomIds.push(id)
  }

  /* ① まだ卓に居る人を反映 */
  bill.stays
      .filter(s => !s.left_at)                // アクティブだけ
      .forEach(s => {
        const id   = Number(s.cast.id)
        const kind = id === castId ? nextKind   // ← ここで差し替え
                                    : s.stay_type
        push(id, kind)
      })

  /* ② クリックした本人が含まれていなければ追加して上書き */
  if (![...lists.freeIds, ...lists.inIds, ...lists.nomIds].includes(castId)) {
    push(castId, nextKind)                    // 新しい kind で追加
  }
  /* 3) 3 配列まとめて送信 → 上書きされても全員残る */
  await updateBillCasts(billId, lists)

  await billsStore.loadAll()            // UI / モーダルを同期
}
// ────────────────────────────────
//  DnD ハンドラ
// ────────────────────────────────
/* 共通 : stay 配列から lists を組み立てる */
function makeLists(bill, extra = []) {
  const lists = { freeIds: [], inIds: [], nomIds: [] }
  const push  = (id, kind) => {
    if (kind === 'free') lists.freeIds.push(id)
    else if (kind === 'in') lists.inIds.push(id)
    else                    lists.nomIds.push(id)
  }

  bill.stays
      .filter(s => !s.left_at)
      .forEach(s => push(Number(s.cast.id), s.stay_type))

  /* 追加で放り込みたい id(kind=free) があれば付け足す */
  extra.forEach(id => { if (!lists.freeIds.includes(id)) lists.freeIds.push(id) })

  return lists
}

/* ───────── DnD ハンドラ改修 ───────── */
async function handleUpdateStay({ castId, fromBillId, toBillId, toTableId }) {
  /* --------------------------------------------
   * ① 同じ Bill 内の並び替え
   * -------------------------------------------- */
  if (fromBillId && fromBillId === toBillId) {
    const bill = billsStore.list.find(b => b.id === fromBillId)
    if (bill) {
      /* 並び順だけ最新にして丸ごと送信 */
      const lists = makeLists(bill)
      await updateBillCasts(fromBillId, lists)
      await billsStore.loadAll()
    }
    return                                  // ← ここで完結
  }
  /* ② 元 Bill : 抜けた子を除いて再送信 --------- */
  if (fromBillId) {
    const bill = billsStore.list.find(b => b.id === fromBillId)
    if (bill) {
      const lists = makeLists(bill)          // 現状を丸ごと取得
      ['freeIds','inIds','nomIds'].forEach(k=>{
        lists[k] = lists[k].filter(id => id !== castId)
      })
      await updateBillCasts(fromBillId, lists)
    }
  }

  /* ③ 先 Bill : 既存＋新しい子を free で追加 ---- */
  if (toBillId) {
    const bill = billsStore.list.find(b => b.id === toBillId)
    if (bill) {
      const lists = makeLists(bill, [castId])  // extra に新ID
      await updateBillCasts(toBillId, lists)
    }
  }

  /* ④ 空卓 → 新規 Bill を作って free で追加 ---- */
  if (!toBillId && toTableId) {
    const newBill = await createBill({ table_id: toTableId })
    await updateBillCasts(newBill.id, { freeIds: [castId] })
  }

  /* ⑤ 最後にストアを同期 ------------------------ */
  await billsStore.loadAll()
}


// ────────────────────────────────
//  Bill モーダル
// ────────────────────────────────

async function handleSaved(payload) {
  const fresh = typeof payload === 'number' ? await fetchBill(payload) : payload
  if (!fresh) return

  // upsert（置換 or 追加）
  const idx = billsStore.list.findIndex(b => b.id === fresh.id)
  if (idx >= 0) billsStore.list[idx] = fresh
  else billsStore.list.push(fresh)

  // ついでに当日のシフト/空きも同期（表示の色分け用）
  await loadCastsAndShifts()

  // 最後にモーダルを閉じる
  showModal.value = false
}

function openModal (table) {
  const hit = getOpenBill(table.id)
  if (hit) {
    fetchBill(hit.id).then(b => {
      currentBill.value = { ...b, table_id_hint: table.id }
      showModal.value = true
    })
    return
  }
  // 新規：ここでは作らない。ドラフトを渡すだけ
  currentBill.value = {
    id: null,                      // ← BillModal 側の isNew が true になる
    table: { id: table.id, number: table.number, store: table.store },
    table_id_hint: table.id,
    items: [],
    stays: [],
    customers: [],
    opened_at: dayjs().toISOString(),
    expected_out: null,
    grand_total: 0,
  }
  showModal.value = true
}

const closeModal = async () => {
  showModal.value = false
  // ❶ Bill 一覧を再取得
  // ❷ キャストの出勤・空き状況も更新
  await Promise.all([
    billsStore.loadAll(),
    loadCastsAndShifts()
  ])
}

/* BillModal からの @updated 用 : 伝票だけ再取得  */
async function refreshBills () {
  await billsStore.loadAll()
}


// 重複チェック（ダミー）
function checkDuplicates () {}
</script>

<template>
  <section>
    <div class="d-flex justify-content-between">
      <div class="d-flex gap-1 mb-2">
        <span class="badge bg-danger">本指名</span>
        <span class="badge bg-success">場内</span>
        <span class="badge bg-blue">フリー(~10分)</span>
        <span class="badge bg-warning">フリー(~20分)</span>
        <span class="badge bg-orange">フリー(~30分)</span>
      </div>
    </div>
    <div class="tables">
      <div class="bench-cast d-flex justify-content-center bg-white flex-wrap bg-white w-100">
        <!-- 空きキャスト列 -->
        <CastTableDnD
          :bill-id="null"
          :table-id="null"
          :casts="unassigned.slice()"
          :bench-area="true"
          @update-stay="handleUpdateStay"
        />
      </div>

      <!-- テーブルごとの列 -->
      <div class="tables-main d-grid gap-4 mt-4">
        <div
          v-for="t in tables"
          :key="t.id"
          class="table-wrap"
          @pointerdown="onPD(t, $event)"
          @pointermove="onPM"
          @pointerup="onPU(t)"
          @pointercancel="onPC"
          @pointerleave="onPC"
        >
          <CastTableDnD
            :title="`${t.number}`"
            :bill-id="getOpenBill(t.id)?.id ?? null"
            :table-id="t.id"
            :remain-min="calcRemainMin(getOpenBill(t.id))"
            :pax="getOpenBill(t.id)?.pax ?? null"
            :subtotal="getOpenBill(t.id)?.subtotal ?? null"
            :casts="(getOpenBill(t.id)?.stays || []).filter(s=>!s.left_at).map(s=>({
              id: s.cast.id,
              name: s.cast.stage_name,
              avatar: s.cast.avatar_url,
              kind: s.stay_type,
              entered_at: s.entered_at
            }))"
            @update-stay="handleUpdateStay"
            @toggle-stay="handleToggleStay"
          />
        </div>
      </div>

    </div>

    <BillModal
      v-model="showModal"
      :bill="currentBill"
      @saved="handleSaved"
      @updated="refreshBills"
    />
  </section>
</template>

<style scoped>
.table-wrap { touch-action: manipulation; } /* ダブルタップズーム/300ms遅延の抑制 */
</style>