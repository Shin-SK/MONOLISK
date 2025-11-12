<!-- frontend/src/components/BillTablesSP.vue -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'
import { useBills }    from '@/stores/useBills'
import { useTables }   from '@/stores/useTables'
import { fetchCastShifts, getBillingCasts } from '@/api'

const emit = defineEmits(['bill-click','request-new'])

const billsStore  = useBills()
const tablesStore = useTables()

const castsAll    = ref([])
const shiftsToday = ref([])
const tick        = ref(Date.now())
const todayISO    = dayjs().format('YYYY-MM-DD')

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
  await Promise.all([ billsStore.loadAll(), tablesStore.fetch(), loadCastsAndShifts() ])
  startPolling()
})
onBeforeUnmount(stopPolling)

/* 参照 */
const tables = computed(() => tablesStore.list)
const openBillMap = computed(() => {
  const m = new Map()
  billsStore.list.forEach(b => { if (!b.closed_at) m.set(b.table?.id || b.table, b) })
  return m
})
const getOpenBill = id => openBillMap.value.get(id) ?? null

/* 表示ロジック（PCと同じ） */
function calcRemainMin(bill) {
  if (!bill) return null
  const elapsed = dayjs().diff(dayjs(bill.opened_at), 'minute')
  const limit   = bill.round_min || 60
  return Math.max(limit - elapsed, 0)
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

//ゴースト対策
function activeStaysForTable(tableId) {
  const b = getOpenBill(tableId)
  // getOpenBill は closed を原則除外してるが、楽観反映の順序次第で
  // 一瞬入ってくることがあるのでダブルチェック
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
onBeforeUnmount(() => document.removeEventListener('visibilitychange', onVis))

/* 親からの再読込 */
function reload(){ billsStore.loadAll(); refreshShifts() }
defineExpose({ reload })
</script>

<template>
  <!-- ★ あなたのSCSSに合わせる：この配下の構造/クラスはPCと同じ -->
  <section class="tables">
    <!-- ベンチ（表示のみ） -->
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

    <!-- テーブル（PCと同じブロック構造/装飾、DnDだけ無し） -->
    <div class="tables-main d-grid gap-4 mt-4">
      <div
        v-for="t in tables"
        :key="t.id"
        class="table-wrap"
        @click="onTapTable(t)"
      >

        <!-- 本体（PCと同じ：空席はラベル、在席時はキャスト一覧） -->
        <div class="table-box h-100 d-flex flex-column bg-white">
          <!-- 空席 -->
          <div
            v-if="!getOpenBill(t.id)"
            class="vacant-label flex-grow-1 d-flex justify-content-center align-items-center fs-3 bg-secondary text-light"
            style="min-height: 100px;"
          >
            <div class="d-flex align-items-center gap-2">
              <IconPinned :size="22" />
              <span class="fw-bold">{{ t.number }}</span>
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
                is_help: s.is_help === true,   // ← これを渡す！
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

        <!-- フッター（PCと同じ .sum 相当の情報帯） -->
        <div
          v-if="getOpenBill(t.id) && !getOpenBill(t.id).closed_at"
          class="sum bg-white p-2 d-flex gap-3 justify-content-between align-items-center fs-5"
        >
          <div class="table-number align-items-center gap-1 d-md-none d-flex">
            <IconPinned :size="20"/>
            <span>{{ t.number }}</span>
          </div>

          <div v-if="getOpenBill(t.id)?.id != null" class="item d-flex gap-1 align-items-center d-md-none d-flex">
            <IconNotes :size="20"/>
            <span>{{ getOpenBill(t.id)?.id }}</span>
          </div>

          <div v-if="getOpenBill(t.id)?.pax != null" class="item d-md-none d-flex">
            <IconUsers />{{ getOpenBill(t.id)?.pax }}
          </div>

          <div v-if="calcRemainMin(getOpenBill(t.id)) !== null" class="item d-flex gap-2 align-items-center">
            <IconHistoryToggle :size="20"/><span>{{ calcRemainMin(getOpenBill(t.id)) }}分</span>
          </div>

          <div v-if="getOpenBill(t.id)?.subtotal != null" class="item d-flex gap-0 align-items-center">
            <IconCurrencyYen :size="20"/>
            <span class="d-flex align-items-center">
              {{ (getOpenBill(t.id)?.subtotal||0).toLocaleString() }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
