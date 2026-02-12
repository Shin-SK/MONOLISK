<!-- frontend/src/components/BillBoardPC.vue -->
<!-- 伝票中心の卓ビュー（PC用）: 表示単位 = Open Bill + CastTableDnD -->
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
  getBillingCasts,
} from '@/api'
import { useTables }  from '@/stores/useTables'
import { useCasts }   from '@/stores/useCasts'
import { tableIdsOfBill, buildOpenBillMap, billTableLabel } from '@/utils/billTableHelpers'

// ────────────────────────────────
//  state
// ────────────────────────────────
const billsStore  = useBills()
const tablesStore = useTables()
const castsStore  = useCasts()

const castsAll    = ref([])
const shiftsToday = ref([])
const currentBill = ref(null)
const showModal   = ref(false)
const todayISO    = dayjs().format('YYYY-MM-DD')

// ────────────────────────────────
//  初期ロード
// ────────────────────────────────
async function loadCastsAndShifts () {
  const [casts, shifts] = await Promise.all([
    getBillingCasts({ _ts: Date.now() }, { cache: false }),
    fetchCastShifts({ date: todayISO })
  ])
  castsAll.value    = Array.isArray(casts) ? casts : []
  shiftsToday.value = Array.isArray(shifts) ? shifts : []
}

onMounted(async () => {
  await Promise.all([
    billsStore.loadAll(),
    tablesStore.fetch(),
    loadCastsAndShifts(),
  ])
})

// ────────────────────────────────
//  テーブル ID → テーブルオブジェクト
// ────────────────────────────────
const tablesById = computed(() => {
  const m = new Map()
  tablesStore.list.forEach(t => m.set(Number(t.id), t))
  return m
})

// ────────────────────────────────
//  M2M 対応 Bill マップ
// ────────────────────────────────
const openBillMap = computed(() => buildOpenBillMap(billsStore.list))
const getOpenBill = id => openBillMap.value.get(Number(id)) ?? null

// ────────────────────────────────
//  占有テーブル ID 集合 / 空卓 / Open 伝票
// ────────────────────────────────
const occupiedTableIds = computed(() => new Set(openBillMap.value.keys()))

const vacantTables = computed(() =>
  tablesStore.list.filter(t => !occupiedTableIds.value.has(Number(t.id)))
)

const openBills = computed(() => {
  const seen = new Set()
  return billsStore.list.filter(b => {
    if (b.closed_at) return false
    if (seen.has(b.id)) return false
    const tids = tableIdsOfBill(b)
    if (!tids.length) return false
    seen.add(b.id)
    return true
  })
})

// ────────────────────────────────
//  空卓の複数選択
// ────────────────────────────────
const selectedVacant = ref(new Set())

function toggleVacant(tableId) {
  const s = new Set(selectedVacant.value)
  if (s.has(tableId)) s.delete(tableId)
  else s.add(tableId)
  selectedVacant.value = s
}

function createFromSelected() {
  const ids = [...selectedVacant.value]
  if (!ids.length) return
  emit('request-new', { tableIds: ids })
  selectedVacant.value = new Set()
}

function onClickVacant(table) {
  if (selectedVacant.value.size > 0) {
    toggleVacant(table.id)
  } else {
    emit('request-new', { tableId: table.id })
  }
}

const emit = defineEmits(['bill-click', 'request-new'])

function calcRemainMin(bill) {
  if (!bill) return null
  const elapsed = dayjs().diff(dayjs(bill.opened_at), 'minute')
  const limit   = bill.round_min || 60
  return Math.max(limit - elapsed, 0)
}

// ── ポインタイベント（クリック vs ドラッグ判定） ──
const CLICK_TOL = 8
const press = ref(null)

function onPD(bill, e) {
  press.value = { id: bill.id, x: e.clientX, y: e.clientY, moved: false }
}
function onPM(e) {
  if (!press.value) return
  if (Math.abs(e.clientX - press.value.x) > CLICK_TOL ||
      Math.abs(e.clientY - press.value.y) > CLICK_TOL) {
    press.value.moved = true
  }
}
function onPU(bill) {
  if (!press.value) return
  const moved = press.value.moved
  press.value = null
  if (!moved) openModal(bill)
}
function onPC() { press.value = null }

// ────────────────────────────────
//  ポーリング
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

watch(showModal, async (v) => {
  if (v) {
    stopPolling()
  } else {
    await billsStore.loadAll()
    await refreshShifts()
    startPolling()
  }
})

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
//  空きキャスト算出
// ────────────────────────────────
const unassigned = computed(() => {
  const stayIds = new Set(
    billsStore.list.flatMap(b => (b.stays||[])
      .filter(s => !s.left_at)
      .map(s => Number(s.cast.id)))
  )
  const presentIds = new Set(
    shiftsToday.value
      .filter(s => s.clock_in && !s.clock_out)
      .map(s => Number(s.cast.id))
  )
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
async function handleToggleStay({ castId, billId, nextKind }) {
  const bill = billsStore.list.find(b => b.id === billId)
  if (!bill) return

  const lists = { freeIds: [], inIds: [], nomIds: [] }
  const push = (id, kind) => {
    if (kind === 'free') lists.freeIds.push(id)
    else if (kind === 'in') lists.inIds.push(id)
    else lists.nomIds.push(id)
  }

  bill.stays
      .filter(s => !s.left_at)
      .forEach(s => {
        const id   = Number(s.cast.id)
        const kind = id === castId ? nextKind : s.stay_type
        push(id, kind)
      })

  if (![...lists.freeIds, ...lists.inIds, ...lists.nomIds].includes(castId)) {
    push(castId, nextKind)
  }
  await updateBillCasts(billId, lists)
  await billsStore.loadAll()
}

// ────────────────────────────────
//  DnD ハンドラ
// ────────────────────────────────
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

  extra.forEach(id => { if (!lists.freeIds.includes(id)) lists.freeIds.push(id) })

  return lists
}

async function handleUpdateStay({ castId, fromBillId, toBillId, toTableId }) {
  if (fromBillId && fromBillId === toBillId) {
    const bill = billsStore.list.find(b => b.id === fromBillId)
    if (bill) {
      const lists = makeLists(bill)
      await updateBillCasts(fromBillId, lists)
      await billsStore.loadAll()
    }
    return
  }

  if (fromBillId) {
    const bill = billsStore.list.find(b => b.id === fromBillId)
    if (bill) {
      const lists = makeLists(bill)
      ;['freeIds','inIds','nomIds'].forEach(k=>{
        lists[k] = lists[k].filter(id => id !== castId)
      })
      await updateBillCasts(fromBillId, lists)
    }
  }

  if (toBillId) {
    const bill = billsStore.list.find(b => b.id === toBillId)
    if (bill) {
      const lists = makeLists(bill, [castId])
      await updateBillCasts(toBillId, lists)
    }
  }

  if (!toBillId && toTableId) {
    const newBill = await createBill({ table_id: toTableId })
    await updateBillCasts(newBill.id, { freeIds: [castId] })
  }

  await billsStore.loadAll()
}

// ────────────────────────────────
//  Bill モーダル
// ────────────────────────────────
async function handleSaved(payload) {
  const fresh = typeof payload === 'number' ? await fetchBill(payload) : payload
  if (!fresh) return

  const idx = billsStore.list.findIndex(b => b.id === fresh.id)
  if (idx >= 0) billsStore.list[idx] = fresh
  else billsStore.list.push(fresh)

  await loadCastsAndShifts()
  showModal.value = false
}

function openModal (bill) {
  fetchBill(bill.id).then(b => {
    currentBill.value = { ...b, table_id_hint: tableIdsOfBill(bill)[0] ?? null }
    showModal.value = true
  })
}

const closeModal = async () => {
  showModal.value = false
  await Promise.all([
    billsStore.loadAll(),
    loadCastsAndShifts()
  ])
}

async function refreshBills () {
  await billsStore.loadAll()
}

/* 親からの再読込 */
function reload(){ billsStore.loadAll(); refreshShifts() }
defineExpose({ reload })
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
      <!-- ベンチ（空きキャスト DnD） -->
      <div class="bench-cast d-flex justify-content-center bg-white flex-wrap bg-white w-100">
        <CastTableDnD
          :bill-id="null"
          :table-id="null"
          :casts="unassigned.slice()"
          :bench-area="true"
          @update-stay="handleUpdateStay"
        />
      </div>

      <!-- 空卓セクション -->
      <div class="vacant-section mt-4 p-3 bg-light rounded">
        <h6 class="fw-bold text-secondary mb-2">
          <IconPinned :size="18" /> 空きテーブル
        </h6>
        <div v-if="vacantTables.length" class="d-flex flex-wrap gap-2">
          <button
            v-for="t in vacantTables"
            :key="t.id"
            class="btn"
            :class="selectedVacant.has(t.id) ? 'btn-primary' : 'btn-outline-secondary'"
            @click="onClickVacant(t)"
            @contextmenu.prevent="toggleVacant(t.id)"
          >
            {{ t.number }}
          </button>
        </div>
        <div v-else class="text-muted small">全卓使用中</div>

        <div v-if="selectedVacant.size > 0" class="mt-2 d-flex align-items-center gap-2">
          <button class="btn btn-primary" @click="createFromSelected">
            選択した {{ selectedVacant.size }} 卓で新規伝票を作成
          </button>
          <button class="btn btn-outline-secondary btn-sm" @click="selectedVacant = new Set()">
            選択解除
          </button>
        </div>
      </div>

      <!-- Open 伝票カラム -->
      <div class="tables-main d-grid gap-4 mt-4">
        <div
          v-for="bill in openBills"
          :key="bill.id"
          class="table-wrap"
          @pointerdown="onPD(bill, $event)"
          @pointermove="onPM"
          @pointerup="onPU(bill)"
          @pointercancel="onPC"
          @pointerleave="onPC"
        >
          <CastTableDnD
            :title="billTableLabel(bill, tablesById)"
            :bill-id="bill.id"
            :table-id="tableIdsOfBill(bill)[0] ?? null"
            :remain-min="calcRemainMin(bill)"
            :pax="bill.pax ?? null"
            :subtotal="bill.subtotal ?? null"
            :casts="(bill.stays || []).filter(s=>!s.left_at).map(s=>({
              id: s.cast.id,
              name: s.cast.stage_name,
              avatar: s.cast.avatar_url,
              kind: s.stay_type,
              entered_at: s.entered_at,
              is_help: s.is_help === true
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
.table-wrap { touch-action: manipulation; }
</style>
