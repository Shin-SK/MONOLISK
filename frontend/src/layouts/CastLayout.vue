<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { 
  fetchBills,
  fetchCastMypage,
  fetchCastShiftHistory,
  fetchCastDailySummaries,
  fetchCastRankings,
  listCastGoals,
  fetchPayrollStatus,
} from '@/api'
import CastSidebar from '@/components/sidebar/CastSidebar.vue'
import CastOrderModal from '@/components/cast/CastOrderModal.vue'
import { useCastEvents } from '@/stores/useCastEvents'
import { useProfile } from '@/composables/useProfile'
import RefreshAvatar from '@/components/RefreshAvatar.vue'
import Avatar from '@/components/Avatar.vue'
import { installAutoCloseOnRoute, openOffcanvas } from '@/utils/bsOffcanvas'
import { yen } from '@/utils/money'
import dayjs from 'dayjs'

const router = useRouter()
const route  = useRoute()
const user   = useUser()
const { avatarURL, displayName } = useProfile() 

/* ---------- castId解決 ---------- */
const castId = ref(null)

async function resolveCastId() {
  // URLに :id があればそれを優先
  const idParam = Number(route.params.id)
  if (!Number.isNaN(idParam)) { castId.value = idParam; return }

  // なければ /api/me から cast_id を取得
  if (!user.me) {
    try { await user.fetchMe?.() } catch {}
  }
  if (user.me?.cast_id) {
    castId.value = user.me.cast_id
    return
  }
}

/* ---------- ヘッダー用データ ---------- */
const castInfo = ref(null)
const shifts = ref([])
const todaySum = ref(null)
const rankings = ref([])
const latestGoal = ref(null)
const payrollStatus = ref(null)
const goalProgressMap = ref({})
const todayStr = dayjs().format('YYYY-MM-DD')
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ取得 ---------- */
async function loadCast() {
  if (!castId.value) return
  castInfo.value = await fetchCastMypage(castId.value)
}

async function loadShifts() {
  if (!castId.value) return
  shifts.value = await fetchCastShiftHistory(castId.value, {
    from: dateFrom.value,
    to: dateTo.value,
  })
}

async function loadToday() {
  if (!castId.value) return
  const list = await fetchCastDailySummaries({
    cast: castId.value,
    from: todayStr,
    to: todayStr,
  })
  todaySum.value = list[0] ?? null
}

async function loadRankings() {
  rankings.value = await fetchCastRankings({
    from: dateFrom.value,
    to: dateTo.value,
  })
}

async function loadLatestGoal() {
  if (!castId.value) return
  try {
    const goals = await listCastGoals(castId.value)
    if (Array.isArray(goals) && goals.length > 0) {
      latestGoal.value = goals[0]
      goalProgressMap.value[goals[0].id] = {
        value: goals[0].progress_value ?? 0,
        percent: goals[0].progress_percent ?? 0,
        milestones: {
          50: (goals[0].hits || []).includes(50),
          80: (goals[0].hits || []).includes(80),
          90: (goals[0].hits || []).includes(90),
          100: (goals[0].hits || []).includes(100),
        }
      }
    } else {
      latestGoal.value = null
    }
  } catch (e) {
    console.error('loadLatestGoal failed:', e)
    latestGoal.value = null
  }
}

async function loadPayrollStatus() {
  try {
    payrollStatus.value = await fetchPayrollStatus()
  } catch (e) {
    console.error('loadPayrollStatus failed:', e)
    payrollStatus.value = null
  }
}

async function loadHeaderData() {
  await Promise.all([
    loadCast(),
    loadShifts(),
    loadToday(),
    loadRankings(),
    loadLatestGoal(),
    loadPayrollStatus(),
  ])
}

/* ---------- computed ---------- */
const avatarUrl = computed(() =>
  castInfo.value?.avatar_url || avatarURL.value || ''
)

const todaySales = computed(() =>
  todaySum.value ? todaySum.value.total + todaySum.value.payroll : null
)

const myRank = computed(() => {
  const idx = rankings.value.findIndex(r => r.cast_id === castId.value)
  return idx === -1 ? null : idx + 1
})

const gardenRank = computed(() => {
  const s = payrollStatus.value
  if (!s || s.enabled === false) return null
  return s.rank || null
})

const nextShift = computed(() => {
  const now = dayjs()
  return shifts.value
    .filter(s => s.plan_start && dayjs(s.plan_start).isAfter(now))
    .sort((a,b) => dayjs(a.plan_start) - dayjs(b.plan_start))[0] || null
})

const nextShiftDate = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_start).format('YYYY/MM/DD') : null
)

const nextShiftStart = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_start).format('HH:mm') : null
)

const nextShiftEnd = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_end).format('HH:mm') : null
)

const latestGoalView = computed(() => {
  if (!latestGoal.value) return null
  const g = latestGoal.value
  const DISPLAY_META = {
    revenue:        { name: '売上金額',       unit: '円' },
    nominations:    { name: '本指名 本数',     unit: '本' },
    inhouse:        { name: '場内指名 本数',   unit: '本' },
    champ_revenue:  { name: 'シャンパン売上',   unit: '円' },
    champ_count:    { name: 'シャンパン本数',   unit: '本' },
  }
  const meta = DISPLAY_META[g.metric] || { name: g.metric, unit: '' }
  const isMoney = meta.unit === '円'
  const fmtYen = (n) => '¥' + (Number(n) || 0).toLocaleString()
  
  const s = g.start_date || g.period_from
  const e = g.end_date || g.period_to
  const curVal = goalProgressMap.value[g.id]?.value ?? 0
  const pct = goalProgressMap.value[g.id]?.percent ?? 0
  
  const fmtTarget = isMoney ? fmtYen(g.target_value) : `${g.target_value} ${meta.unit || ''}`.trim()
  const fmtCurrent = isMoney ? fmtYen(curVal) : `${curVal} ${meta.unit || ''}`.trim()
  
  return {
    label: meta.name,
    from: dayjs(s).format('MM/DD'),
    to: dayjs(e).format('MM/DD'),
    targetPretty: fmtTarget,
    currentPretty: fmtCurrent,
    percent: pct,
    milestones: goalProgressMap.value[g.id]?.milestones || {}
  }
})

function openSidebar(){
  openOffcanvas('#castSidebar')
}

/* ---------- タブ ---------- */
const activeTab = computed(() => {
  const path = route.path
  if (path.includes('/goals')) return 'goals'
  if (path.includes('/shift') || path.includes('/apply')) return 'apply'
  if (path.includes('/sales')) return 'sales'
  if (path.includes('/customer')) return 'customers'
  return 'home'
})

function setTab(k) {
  // タブに応じてルーティング
  const routes = {
    home: '/cast/mypage',
    apply: '/cast/mypage',  // Mypage内のタブ切り替え用
    goals: '/cast/mypage',
    sales: '/cast/mypage',
    customers: '/cast/mypage'
  }
  
  if (routes[k]) {
    router.push(routes[k])
    // Mypageのタブを切り替えるイベントを発火
    window.dispatchEvent(new CustomEvent('cast:tab:change', { detail: { tab: k } }))
  }
}

const candidates = ref([])      // 本指名で「自卓」注文できる Bill 候補
const singleBillId = computed(() => candidates.value.length === 1 ? candidates.value[0].id : null)
const hasSelfOrder = computed(() => candidates.value.length > 0)
const showOrderModal = ref(false)
const selectedBillIdForOrder = ref(null)

/** 自分（me.cast_id）が在席中＆本指名の Bill を抽出 */
async function resolveSelfOrderTargets() {
  if (!user.me) await user.fetchMe?.()
  const meCastId = user.me?.cast_id
  if (!meCastId) { candidates.value = []; return }

  const data  = await fetchBills({ limit: 200 })
  const bills = Array.isArray(data.results) ? data.results : data
  const hits = []
  for (const b of bills) {
    const stays = b.stays || []
    const ok = stays.some(s =>
      (s.cast?.id === meCastId) &&
      (s.is_honshimei === true || s.stay_type === 'nom') &&
      !s.left_at
    )
    if (ok) hits.push({ id: b.id, tableName: b.table?.name || `#${b.table?.id || '-'}` })
  }
  candidates.value = hits
}

function goOrder() {
  selectedBillIdForOrder.value = singleBillId.value || null
  showOrderModal.value = true
}

function closeOrderModal() {
  showOrderModal.value = false
  selectedBillIdForOrder.value = null
}

/* ===== 伝票画面かどうか／キャストフッターの表示制御 ===== */
const isOrderPage     = computed(() => route.path.startsWith('/cast/order'))
const showCastFooter  = ref(!isOrderPage.value)
watch(isOrderPage, v => { showCastFooter.value = !v })
function toggleCastFooter(){
  if (isOrderPage.value) showCastFooter.value = !showCastFooter.value
}

function handleBillClosed(){ resolveSelfOrderTargets() }

function handleSelfOrderUpdate(){ resolveSelfOrderTargets() }

let castEvents = null
function handleEvents(evts){
  // どのイベントでもいったん候補を取り直す（十分に軽い）
  resolveSelfOrderTargets()
  // ついでにバッジ用の数が来たら反映したい場合はここで拾う
  // const e = Array.isArray(evts) ? evts.find(v => v?.type==='selforder_count') : null
  // if (e) selfOrderCount.value = e.count
}

onMounted(async () => {
  installAutoCloseOnRoute(router)
  await resolveCastId()                       // castId解決
  await loadHeaderData()                      // ヘッダーデータ読み込み
  await resolveSelfOrderTargets()             // me取得も内包してるのでawait
  window.addEventListener('bill:closed', handleBillClosed)
  window.addEventListener('cast:selforder:update', handleSelfOrderUpdate)
  if (user.me?.cast_id) {
    castEvents = useCastEvents(user.me, handleEvents)
    castEvents.start()                        // ★開始
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('bill:closed', handleBillClosed)
  window.removeEventListener('cast:selforder:update', handleSelfOrderUpdate) 
  castEvents?.stop() 
})
watch(() => route.fullPath, (p) => {
  if (p.startsWith('/cast/')) resolveSelfOrderTargets()
})
</script>

<template>
  <div class="cast-layout min-vh-100 d-flex flex-column">

    <!-- 中央：自卓オーダー直行（伝票画面では非表示） -->
    <div v-if="hasSelfOrder && !isOrderPage"
      class="position-fixed"
      style="bottom: 72px; right: 24px; z-index: 999;">
      <button
        class="btn btn-danger rounded-circle p-2 shadow-sm fs-1 d-flex align-items-center jusify-content-center"
        @click="goOrder"
        aria-label="自卓オーダーへ"
      >
        <!-- ← アイコンの色は text-white (= stroke: #fff) -->
        <IconFileInvoice :size="40" :stroke="1.5"/>
      </button>
    </div>

    <header class="header mb-4 container mt-3">
      <div class="upper mb-2 d-flex align-items-center justify-content-between">
        <h2 class="fs-2 fw-bold">マイページ</h2>
        <button @click="openSidebar"><IconMenuDeep class="fs-5"/></button><!-- サイドバー開く -->
      </div>
        
      <div class="user-meta d-flex align-items-center justify-content-between mb-4">
        <div class="wrap w-100 d-flex align-items-center justify-content-between">
          <div class="avatars d-flex align-items-center gap-2">
            <Avatar :url="avatarUrl" :size="40" class="rounded-circle"/>
            <div class="name">
              <div class="fs-5 fw-bold m-0">
                {{ castInfo?.stage_name || 'キャスト名' }}
              </div>
              <div class="wrap">
                <div v-if="todaySales !== null">
                  <span
                    class="small mb-0 d-flex align-items-center gap-1 fw-bold lh-1">
                    <span class="badge bg-light text-dark">今日の売り上げ</span>{{ yen(todaySales)}}
                  </span>
                </div>
                <div v-else class="small wrap d-flex align-items-center gap-2 text-muted">
                  今日もがんばりましょう！
                </div>
              </div>
            </div>
          </div>            
          <div v-if="myRank"
            class="d-flex align-items-center gap-1">
            <IconTrendingUp />
            <span class="fs-5 fw-bold">No.{{ myRank }}</span>
          </div>
          <div v-if="gardenRank" class="d-flex align-items-center gap-2">
            <span class="badge bg-dark">ランク {{ gardenRank }}</span>
          </div>
        </div>
      </div>

      <div class="row g-2">
        <div class="col-12">
          <div class="card px-2 py-3">
            <div v-if="latestGoalView">
              <div class="d-flex align-items-center justify-content-between w-100">
                <div class="date">
                  <small class="text-muted d-flex gap-0">
                    <IconCalendar />
                    <span>{{ latestGoalView.from }}〜</span>
                    <span>{{ latestGoalView.to }}</span>
                  </small>
                </div>
                <div class="d-flex align-items-center gap-1">
                  <IconTargetArrow />
                  <span class="fs-3 fw-bold lh-1 d-block">{{ latestGoalView.currentPretty }}</span>
                  <span class="lh-1">/</span><small class="text-muted lh-1">{{ latestGoalView.targetPretty }}</small>
                </div>
              </div>
            </div>
            <div v-else class="text-muted small">
              目標未設定
            </div>
          </div>
        </div>

        <div class="col-12">
          <div class="card px-2 py-3">
            <div class="d-flex align-items-center justify-content-between">
              <div class="head d-flex align-items-center gap-1 small fw-bold"><IconCalendarPlus />次のシフト</div>
              <div class="inner">
                <div v-if="nextShift" class="d-flex flex-column">
                  <span class="fw-bold">{{ nextShiftDate }}</span>
                  <span class="text-muted">{{ nextShiftStart }} 〜 {{ nextShiftEnd }}</span>
                </div>
                <div v-else class="text-muted small">
                  シフト予定なし
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </header>

    <!-- 本体 -->
    <main class="flex-fill container d-flex flex-column">
      <router-view />
    </main>

    <footer class="position-fixed bottom-0 end-0 start-0 w-100 bg-white py-2">
      <!-- タブ -->
      <nav class="d-flex justify-content-around bg-white">
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'home' }"
          @click="setTab('home')"
        >
          <IconHome />
          <small>ホーム</small>
        </button>
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'apply' }"
          @click="setTab('apply')"
        >
          <IconCalendarPlus />
          <small>シフト</small>
        </button>
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'goals' }"
          @click="setTab('goals')"
        >
          <IconTargetArrow />
          <small>目標</small>
        </button>
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'sales' }"
          @click="setTab('sales')"
        >
          <IconRosetteDiscountCheck />
          <small>売上</small>
        </button>
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'customers' }"
          @click="setTab('customers')"
        >
          <IconFaceId />
          <small>顧客</small>
        </button>
      </nav>
    </footer>
  </div>
    <!-- オフキャンバス（サイドバー） -->
    <CastSidebar />
    
    <!-- 自卓オーダーモーダル -->
    <CastOrderModal 
      v-if="showOrderModal"
      :selected-bill-id="selectedBillIdForOrder"
      :candidates="candidates"
      @close="closeOrderModal"
    />
</template>

<style scoped lang="scss">
.cast-layout main{
  margin-bottom: 64px;
}

/* ── 通常：画面下いっぱいのフッター ── */
.cast-footer{
		padding: 8px 16px;
		position: fixed;
		bottom: 0;
		width: 100%;
		height: auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-direction: row;
		z-index: 999;
		background-color: white;
    .nav-link{
      width: 40px;
      height: 40px;
    }
    .order-button{
      left: 0;
      right: 0;
      bottom: 8px;
      margin: auto;
      width: fit-content;
      color: white;
  }

  &.is-orderpage{
    width: auto;
    left: auto;
    right: .5rem;
    bottom: calc(80px + 80px + 2rem);
    border: 1px solid rgba(0,0,0,.08);
    border-radius: .75rem;
    padding: .75rem;
    box-shadow: 0 8px 24px rgba(0,0,0,.08);
    transform: translateX(110%);
    transition: transform .25s ease;
    &.is-open{
      transform: translateX(0);
    }
    .wrap{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
  }
}

/* 右端のスライド用タブ */
.toggle-tab{
  position: fixed;
  right: 0;
  bottom: calc(80px + 1rem);
  z-index: 99999;
  background: #fff !important;
  border: 1px solid rgba(0,0,0,.1);
  border-right: none;
  border-radius: .75rem 0 0 .75rem;
  padding: 32px 0px;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translateX(0);
}

.toggle-tab.opened svg{ transform: rotate(180deg); transition: transform .2s ease; }
</style>
