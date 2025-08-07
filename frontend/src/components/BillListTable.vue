
<!-- ──────────────────────────────────────────────── -->
<!-- BillListTable.vue                               -->
<!-- 伝票＋キャスト DnD 親コンポーネント               -->
<!-- ──────────────────────────────────────────────── -->

<script setup>
import { ref, computed, onMounted } from 'vue'
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
async function loadCastsAndShifts () {                    // ★名前そのまま
  await Promise.all([
    castsStore.fetch(),                                   // キャスト一覧
    fetchCastShifts({ date: todayISO })
      .then(r => (shiftsToday.value = r)),                // 今日のシフト
  ])
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

// ────────────────────────────────
//  周期リロード（1 分）
// ────────────────────────────────
setInterval(async () => {
  await billsStore.loadAll()
  shiftsToday.value = await fetchCastShifts({ date: todayISO })
}, 60_000)

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
  const presentIds = new Set(
    shiftsToday.value.filter(s => !s.clock_out)
      .map(s => Number(s.cast.id))
  )
  return castsStore.list
    .filter(c => presentIds.has(Number(c.id)) && !stayIds.has(Number(c.id)))
    .map(c => ({
      id:     c.id,
      name:   c.stage_name,
      avatar: c.avatar_url,
      kind:   'free'
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
async function openModal (table) {
  const hit = getOpenBill(table.id)
  if (hit) {
    currentBill.value = { ...(await fetchBill(hit.id)), table_id_hint: table.id }
  } else {
    const created = await createBill({ table_id: table.id })
    currentBill.value = { ...(await fetchBill(created.id)), table_id_hint: table.id }
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
      <div class="bench-cast d-flex gap-5 justify-content-center bg-white flex-wrap bg-white p-5 w-100">
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
        <CastTableDnD
          v-for="t in tables"
          :key="t.id"
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
          @dblclick.native="openModal(t)"
          @toggle-stay="handleToggleStay"
          @click.native="() => { // ★ここ追加
            if (!getOpenBill(t.id)) openModal(t) // Bill 無ければ新規作成
          }"
        />
      </div>
    </div>

    <BillModal
      v-model="showModal"
      :bill="currentBill"
      @saved="closeModal"
      @updated="refreshBills"
    />
  </section>
</template>

<style scoped>
</style>
