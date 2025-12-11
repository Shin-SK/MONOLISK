<!-- frontend/src/components/BillTablesSP.vue -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'
import { useBills }    from '@/stores/useBills'
import { useTables }   from '@/stores/useTables'
import { fetchCastShifts, getBillingCasts } from '@/api'
import { useTableAlerts } from '@/composables/useTableAlerts'

const emit = defineEmits(['bill-click','request-new'])

const billsStore  = useBills()
const tablesStore = useTables()

const castsAll    = ref([])
const shiftsToday = ref([])
const tick        = ref(Date.now())
const todayISO    = dayjs().format('YYYY-MM-DD')

// 初期ロードが完了するまで全体を隠す
const initialLoading = ref(true)

// テーブルアラート検知
const { getAlertState, calcRemainMin: calcRemainMinFromAlert, cleanup: cleanupAlerts } = useTableAlerts(
  computed(() => billsStore.list)
)

/* 初期ロード */
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

/* 参照 */
const tables = computed(() => tablesStore.list)
// ★ 占有判定の純粋化：closed_atがnullの伝票のみを「開いている」と見なす
const openBillMap = computed(() => {
  const m = new Map()
  billsStore.list.forEach(b => {
    // closed_atが存在しない＝未クローズのみ占有扱い
    if (!b.closed_at && b.table) {
      const tid = typeof b.table === 'object' ? b.table.id : b.table
      m.set(tid, b)
    }
  })
  return m
})
const getOpenBill = id => openBillMap.value.get(id) ?? null

function calcRemainMin(bill) {
  if (!bill) return null
  const elapsed = dayjs().diff(dayjs(bill.opened_at), 'minute')
  const limit   = bill.round_min || 60
  return Math.max(limit - elapsed, 0)
}

function calcPax(bill) {
  if (!bill) return 0
  // items から male/female を集計
  const items = bill.items || []
  let male = 0, female = 0
  for (const it of items) {
    const code = it.master?.code || it.code || ''
    if (code.includes('Male')) male += (it.qty || 0)
    else if (code.includes('Female')) female += (it.qty || 0)
  }
  const total = male + female
  // 0の場合は bill.pax をフォールバック
  return total > 0 ? total : (bill.pax || 0)
}

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

/* PCの色分けと同等 */
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
function afterWidth(el){
  if (!el || el.kind !== 'free') return null
  const mins   = dayjs(tick.value).diff(dayjs(el.entered_at),'minute')
  const within = mins % 10
  return `${Math.min(within+1,10)*10}%`
}

/* タップでモーダル */
function onTapTable(table) {
  const hit = getOpenBill(table.id)
  if (hit) emit('bill-click', { billId: hit.id })
  else     emit('request-new', { tableId: table.id })
}

// ★ ゴースト対策強化：占有判定がclosed_at基準なので二重チェック不要だが念の為残す
function activeStaysForTable(tableId) {
  const b = getOpenBill(tableId)
  if (!b || b.closed_at) return []
  return (b.stays || []).filter(s => !s.left_at)
}

/* ポーリング（PCと同等の周期） */
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

/* 親からの再読込 */
function reload(){ billsStore.loadAll(); refreshShifts() }
defineExpose({ reload })
</script>

<template>

  <section
    v-if="initialLoading"
    class="tables-loading d-flex justify-content-center align-items-center"
    style="min-height: 60vh;"
  >
    <div class="text-center">
      <div class="spinner-border text-secondary mb-3" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <div>読み込み中です…</div>
    </div>
  </section>

  <section v-else class="tables">
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

    <div class="d-flex gap-1 mt-4" style="font-size: 14px;">
      <small class="badge bg-danger">本指名</small>
      <small class="badge bg-success">場内</small>
      <small class="badge bg-blue">フリー(~10分)</small>
      <small class="badge bg-warning">フリー(~20分)</small>
      <small class="badge bg-orange">フリー(~30分)</small>
    </div>
    <!-- テーブル -->
    <div class="tables-main d-grid gap-4 mt-2">
      <div
        v-for="t in tables"
        :key="t.id"
        class="table-wrap card"
        :class="{ 'border border-danger': getAlertState(getOpenBill(t.id)) }"
        @click="onTapTable(t)"
      >

        <!-- ヘッダー -->
        <div v-if="getOpenBill(t.id) && !getOpenBill(t.id).closed_at"
          class="sum bg-white p-2 d-flex gap-3 justify-content-between align-items-center fs-5"
        >
          <div class="df-center flex-column gap-1">
            <span class="badge bg-light text-dark m-0 df-center gap-1">
              <IconPinned/>卓番
            </span>
            <span class="fs-4 fw-bold">
              {{ t.number }}</span>
          </div>

          <div class="df-center flex-column gap-1">
            <span class="badge bg-light text-dark m-0 df-center gap-1">
              <IconUsers />客数
            </span>
            <span class="fs-4 fw-bold">
              {{ calcPax(getOpenBill(t.id)) }}</span>
          </div>

          <div class="df-center flex-column gap-1">
            <span class="badge bg-light text-dark m-0 df-center gap-1">
              <IconHistoryToggle :size="20"/>残り
            </span>
            <span class="fs-4 fw-bold">
              {{ calcRemainMin(getOpenBill(t.id)) }}分</span>
          </div>

          <div class="df-center flex-column gap-1">
            <span class="badge bg-light text-dark m-0 df-center gap-1">
              <IconCurrencyYen :size="20"/>小計
            </span>
            <span class="fs-4 fw-bold">
              {{ (getOpenBill(t.id)?.subtotal||0).toLocaleString() }}
            </span>
          </div>
        </div>

        <!-- 本体 -->
        <div class="table-box h-100 d-flex flex-column bg-white">
          <!-- 空席 -->
          <div
            v-if="!getOpenBill(t.id)"
            class="vacant-label flex-grow-1 df-center flex-column bg-secondary text-light"
            style="min-height: 100px;"
          >
            <div class="d-flex align-items-center gap-1">
              <IconPinned :size="22" />
              <span class="fw-bold fs-3">{{ t.number }}</span>
            </div>
            <div class="df-center">
              <span class="badge bg-light text-secondary">伝票を作る</span>
            </div>
          </div>

          <!-- 在席：キャスト一覧（色/残り線も同様） -->
          <div v-else class="casts bg-white d-flex flex-wrap gap-2 p-3">
            <div
              v-for="s in activeStaysForTable(t.id)"
              :key="s.cast.id"
              class="cast-card btn text-light p-2 d-flex align-items-center"
              :class="`bg-${bgColor({
                kind: s.stay_type,
                is_help: s.is_help === true,
                dohan: s.stay_type === 'dohan',
                entered_at: s.entered_at
              })}`"
              :style="afterWidth({ kind: s.stay_type, entered_at: s.entered_at }) ? {'--after-width': afterWidth({ kind: s.stay_type, entered_at: s.entered_at })} : {}"
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
        </div>

        <div class="finish-alert px-2 my-2">
          <span 
            v-if="getAlertState(getOpenBill(t.id))"
            class="alert alert-danger w-100 p-2 df-center m-0 small"
          >
            {{ getAlertState(getOpenBill(t.id)).message }}
          </span>
        </div>  

      </div>
    </div>
  </section>
</template>
