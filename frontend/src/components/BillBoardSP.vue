<!-- frontend/src/components/BillBoardSP.vue -->
<!-- 伝票中心の卓ビュー（SP用）: 表示単位 = Open Bill -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'
import { useBills }    from '@/stores/useBills'
import { useTables }   from '@/stores/useTables'
import { fetchCastShifts, getBillingCasts } from '@/api'
import { useTableAlerts } from '@/composables/useTableAlerts'
import { tableIdsOfBill, buildOpenBillMap, billTableLabel } from '@/utils/billTableHelpers'

const emit = defineEmits(['bill-click', 'request-new'])

const billsStore  = useBills()
const tablesStore = useTables()

const castsAll    = ref([])
const shiftsToday = ref([])
const tick        = ref(Date.now())
const todayISO    = dayjs().format('YYYY-MM-DD')

const initialLoading = ref(true)

const { getAlertState, cleanup: cleanupAlerts } = useTableAlerts(
  computed(() => billsStore.list)
)

/* ── 初期ロード ── */
async function loadCastsAndShifts () {
  const [casts, shifts] = await Promise.all([
    getBillingCasts({ _ts: Date.now() }, { cache: false }),
    fetchCastShifts({ date: todayISO })
  ])
  castsAll.value    = Array.isArray(casts) ? casts : []
  shiftsToday.value = Array.isArray(shifts) ? shifts : []
}
onMounted(async () => {
  initialLoading.value = true
  try {
    await Promise.all([ billsStore.loadAll(), tablesStore.fetch(), loadCastsAndShifts() ])
  } finally {
    initialLoading.value = false
    startPolling()
  }
})
onBeforeUnmount(() => {
  stopPolling()
  cleanupAlerts()
  document.removeEventListener('visibilitychange', onVis)
})

/* ── テーブル ID → テーブルオブジェクト のマップ ── */
const tablesById = computed(() => {
  const m = new Map()
  tablesStore.list.forEach(t => m.set(Number(t.id), t))
  return m
})

/* ── M2M 対応 openBillMap ── */
const openBillMap = computed(() => buildOpenBillMap(billsStore.list))

/* ── 占有テーブル ID の集合 ── */
const occupiedTableIds = computed(() => new Set(openBillMap.value.keys()))

/* ── 空きテーブル ── */
const vacantTables = computed(() =>
  tablesStore.list.filter(t => !occupiedTableIds.value.has(Number(t.id)))
)

/* ── Open 伝票一覧（重複除去）── */
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

/* ── 空卓の複数選択 ── */
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

/* ── 伝票タップ ── */
function onTapBill(bill) {
  emit('bill-click', { billId: bill.id })
}

/* ── 単一空卓タップ（長押しなしの場合） ── */
function onTapVacant(table) {
  if (selectedVacant.value.size > 0) {
    toggleVacant(table.id)
  } else {
    emit('request-new', { tableId: table.id })
  }
}

/* ── 残り時間 ── */
function calcRemainMin(bill) {
  if (!bill) return null
  const elapsed = dayjs().diff(dayjs(bill.opened_at), 'minute')
  const limit   = bill.round_min || 60
  return Math.max(limit - elapsed, 0)
}

/* ── 客数計算 ── */
function calcPax(bill) {
  if (!bill) return 0
  const items = bill.items || []
  let male = 0, female = 0
  for (const it of items) {
    const code = it.master?.code || it.code || ''
    if (code.includes('Male')) male += (it.qty || 0)
    else if (code.includes('Female')) female += (it.qty || 0)
  }
  const total = male + female
  return total > 0 ? total : (bill.pax || 0)
}

/* ── 空きキャスト ── */
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
      kind  : 'free',
      entered_at: dayjs().toISOString()
    }))
})

setInterval(() => (tick.value = Date.now()), 60_000)

/* ── 色分け ── */
function bgColor(el){
  if (!el) return 'primary'
  if (el?.kind === 'dohan' || el?.dohan === true) return 'secondary'
  if (el?.kind === 'free' && el?.is_help) return 'purple'
  if (el.kind === 'free'){
    const mins = dayjs(tick.value).diff(dayjs(el.entered_at),'minute')
    return mins >=30 ? 'orange'
         : mins >=20 ? 'orange'
         : mins >=10 ? 'warning'
         : 'blue'
  }
  return el.kind === 'nom' ? 'danger' : 'success'
}

/* ── ポーリング ── */
let shiftTimer = null
async function refreshShifts() {
  shiftsToday.value = await fetchCastShifts({ date: todayISO }, { silent:true })
}
function startPolling() {
  billsStore.startPolling(60_000)
  if (!shiftTimer) shiftTimer = setInterval(refreshShifts, 60_000)
}
function stopPolling() {
  billsStore.stopPolling()
  if (shiftTimer) { clearInterval(shiftTimer); shiftTimer = null }
}
function onVis() {
  if (document.hidden) stopPolling()
  else { billsStore.loadAll(); refreshShifts(); startPolling() }
}
document.addEventListener('visibilitychange', onVis)
onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVis)
  cleanupAlerts()
})

/* ── 親からの再読込 ── */
function reload(){ billsStore.loadAll(); refreshShifts() }
defineExpose({ reload })
</script>

<template>
  <!-- ローディング -->
  <section
    v-if="initialLoading"
    class="d-flex justify-content-center align-items-center"
    style="min-height: 60vh;"
  >
    <div class="text-center">
      <div class="spinner-border text-secondary mb-3" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <div>読み込み中です…</div>
    </div>
  </section>

  <section v-else class="bill-board-sp">
    <!-- ベンチ（空きキャスト） -->
    <div class="bench-cast d-flex justify-content-center bg-white flex-wrap w-100">
      <div class="table-box w-100">
        <div class="casts d-flex flex-wrap gap-2">
          <div
            v-for="c in unassigned"
            :key="c.id"
            class="p-2 d-flex align-items-center badge bg-secondary"
            style="font-size: 1rem;"
          >
            <span class="small">{{ c.name }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 凡例 -->
    <div class="d-flex gap-1 mt-4" style="font-size: 14px;">
      <small class="badge bg-danger">本指名</small>
      <small class="badge bg-success">場内</small>
      <small class="badge bg-blue">フリー(~10分)</small>
      <small class="badge bg-warning">フリー(~20分)</small>
      <small class="badge bg-orange">フリー(~30分)</small>
    </div>

    <!-- 空卓セクション -->
    <div class="vacant-section mt-4">
      <h6 class="fw-bold text-secondary mb-2">
        <IconPinned :size="18" /> 空きテーブル
      </h6>
      <div v-if="vacantTables.length" class="vacant-grid">
        <button
          v-for="t in vacantTables"
          :key="t.id"
          class="btn"
          :class="selectedVacant.has(t.id) ? 'btn-primary' : 'btn-outline-secondary'"
          @click="onTapVacant(t)"
          @contextmenu.prevent="toggleVacant(t.id)"
        >
          {{ t.number }}
        </button>
      </div>
      <div v-else class="text-muted small">全卓使用中</div>

      <!-- 複数選択時の新規伝票ボタン -->
      <div v-if="selectedVacant.size > 0" class="mt-2 d-flex align-items-center gap-2">
        <button class="btn btn-primary" @click="createFromSelected">
          選択した {{ selectedVacant.size }} 卓で新規伝票を作成
        </button>
        <button class="btn btn-outline-secondary btn-sm" @click="selectedVacant = new Set()">
          選択解除
        </button>
      </div>
    </div>

    <!-- Open 伝票カード一覧 -->
    <div class="bills-section mt-4 d-grid gap-4">
      <div
        v-for="bill in openBills"
        :key="bill.id"
        class="bill-card card"
        :class="{ 'border border-danger': getAlertState(bill) }"
        @click="onTapBill(bill)"
      >
        <!-- ヘッダー -->
        <div v-if="bill.display_name && String(bill.display_name).trim()" class="display-name df-center w-100 bg-white p-1">
          <span  class="fs-4 fw-bold text-primary">
            {{ bill.display_name }}
          </span>
        </div>
        <div class="sum bg-white p-2 d-flex gap-3 justify-content-between align-items-center fs-5">
          <div class="df-center flex-column gap-1">
            <span class="badge bg-light text-dark m-0 df-center gap-1">
              <IconPinned/>卓
            </span>
            <span class="fs-4 fw-bold">
              {{ billTableLabel(bill, tablesById) }}
            </span>
          </div>

          <div class="df-center flex-column gap-1">
            <span class="badge bg-light text-dark m-0 df-center gap-1">
              <IconUsers />客数
            </span>
            <span class="fs-4 fw-bold">
              {{ calcPax(bill) }}
            </span>
          </div>

          <div class="df-center flex-column gap-1">
            <span class="badge bg-light text-dark m-0 df-center gap-1">
              <IconHistoryToggle :size="20"/>残り
            </span>
            <span class="fs-4 fw-bold">
              {{ calcRemainMin(bill) }}分
            </span>
          </div>

          <div class="df-center flex-column gap-1">
            <span class="badge bg-light text-dark m-0 df-center gap-1">
              <IconCurrencyYen :size="20"/>小計
            </span>
            <span class="fs-4 fw-bold">
              {{ (bill.subtotal||0).toLocaleString() }}
            </span>
          </div>
        </div>

        <!-- キャスト一覧 -->
        <div class="casts bg-white d-flex flex-wrap gap-2 p-3">
          <div
            v-for="s in (bill.stays || []).filter(s => !s.left_at)"
            :key="s.cast.id"
            class="cast-card btn text-light p-2 d-flex align-items-center"
            :class="`bg-${bgColor({
              kind: s.stay_type,
              is_help: s.is_help === true,
              dohan: s.stay_type === 'dohan',
              entered_at: s.entered_at
            })}`"
          >
            <Avatar
              :url="s.cast.avatar_url"
              :alt="s.cast.stage_name"
              :size="40"
              class="me-1 rounded-circle"
            />
            {{ s.cast.stage_name }}
          </div>
        </div>

        <!-- アラート -->
        <div class="finish-alert px-2">
          <span
            v-if="getAlertState(bill)"
            class="alert alert-danger w-100 p-2 df-center m-0 small"
          >
            {{ getAlertState(bill).message }}
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.vacant-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}

.vacant-grid .btn {
  width: 100%;
}
</style>
