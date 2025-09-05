<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Avatar from '@/components/Avatar.vue'
import RankingBlock from '@/components/RankingBlock.vue'
import dayjs from 'dayjs'
import {
  fetchBills,
  createCastShift,
  fetchCastShiftHistory,
  fetchCastDailySummaries,
  fetchCastRankings,
  fetchCastMypage,
  fetchStoreNotices
} from '@/api'
import { useUser } from '@/stores/useUser'
import { yen } from '@/utils/money'
import {
  IconCalendarPlus, IconCalendarWeek,
  IconRosetteDiscountCheck, IconFaceId, IconSearch, IconX
} from '@tabler/icons-vue'

/* ---------- 共通 ---------- */
const router = useRouter()
const route  = useRoute()
const user   = useUser()
const isCast = computed(() => !!user.me?.cast_id)  // ★キャストかどうか

/* ---------- キャストID解決（スタッフでも落ちない） ---------- */
const castId = ref(null)
async function resolveCastId() {
  const idParam = Number(route.params.id)
  if (!Number.isNaN(idParam)) { castId.value = idParam; return }
  if (!user.me) { try { await user.fetchMe?.() } catch {} }
  if (user.me?.cast_id) { castId.value = user.me.cast_id; return }
  // スタッフ（cast_idなし）のときはnullのまま進む（アラートしない）
}

/* ---------- 日付 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))
const todayStr = dayjs().format('YYYY-MM-DD')

/* ---------- 状態 ---------- */
const castInfo    = ref(null)
const shifts      = ref([])
const summary     = ref(null)
const todaySum    = ref(null)
const rankings    = ref([])
const notices     = ref([])
const draftShifts = ref([])
const customerBills = ref([])

const openBills = ref([])  // ★スタッフ向け：オープン伝票

/* ---------- タブ（キャスト用UI） ---------- */
const activeTab = ref('apply')
const setTab    = k => (activeTab.value = k)

/* ---------- util ---------- */
const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '–'
const h   = m => m ? (m/60).toFixed(2) : '0.00'

/* ---------- データ取得（castIdありの時だけ叩く） ---------- */
async function loadCast () {
  if (!isCast.value) return
  castInfo.value = await fetchCastMypage(castId.value)
}
async function loadShifts () {
  if (!isCast.value) return
  shifts.value = await fetchCastShiftHistory(castId.value, {
    from: dateFrom.value,
    to  : dateTo.value,
  })
}
async function loadSummary () {
  if (!isCast.value) return
  const list = await fetchCastDailySummaries({
    cast : castId.value,
    from : dateFrom.value,
    to   : dateTo.value,
  })
  summary.value = list[0] ?? null
}
async function loadToday () {
  if (!isCast.value) return
  const list = await fetchCastDailySummaries({
    cast : castId.value,
    from : todayStr,
    to   : todayStr,
  })
  todaySum.value = list[0] ?? null
}
async function loadRankings () {
  if (!isCast.value) return
  rankings.value = await fetchCastRankings({
    from: dateFrom.value,
    to  : dateTo.value,
  })
}
async function loadNotices () {
  const data = await fetchStoreNotices({ status:'published', ordering:'-pinned,-publish_at,-created_at', limit:20 })
  notices.value = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
}
async function loadCustomerBills () {
  if (!isCast.value) { customerBills.value = []; return }
  customerBills.value = (await fetchBills({ cast: castId.value }))
    .filter(b => (b.customer_display_name ?? '').trim().length)
}

/* ★ スタッフ向け：今日のオープン伝票 */
async function loadOpenBills () {
  const data  = await fetchBills({ limit: 50 })
  const bills = Array.isArray(data.results) ? data.results : data
  openBills.value = bills.filter(b => !b.closed_at)
    .sort((a,b)=> dayjs(b.opened_at) - dayjs(a.opened_at))
}

/* 一括 */
async function loadAll () {
  await Promise.all([
    loadCast(), loadShifts(), loadSummary(), loadToday(),
    loadRankings(), loadNotices(), loadCustomerBills(), loadOpenBills()
  ])
}

/* ---------- アバター ---------- */
const avatarUrl = computed(() =>
  castInfo.value?.avatar_url || user.info?.avatar_url || ''
)

/* ---------- 計算（キャストUI） ---------- */
const myRank = computed(() => {
  if (!isCast.value) return null
  const idx = rankings.value.findIndex(r => r.cast_id === castId.value)
  return idx === -1 ? null : idx + 1
})
const nextShift = computed(() => {
  if (!isCast.value) return null
  const now = dayjs()
  return shifts.value
    .filter(s => s.plan_start && dayjs(s.plan_start).isAfter(now))
    .sort((a,b) => dayjs(a.plan_start) - dayjs(b.plan_start))[0] || null
})
const todaySales = computed(() =>
  isCast.value && todaySum.value ? todaySum.value.total + todaySum.value.payroll : null
)
const salesBreakdown = computed(() => isCast.value && summary.value ? {
  champ: summary.value.sales_champ || 0,
  nom  : summary.value.sales_nom   || 0,
  in   : summary.value.sales_in    || 0,
  free : summary.value.sales_free  || 0,
  total: summary.value.total       || 0,
  payroll: summary.value.payroll   || 0,
} : null)

/* ---------- 申請（キャストUIのまま残す） ---------- */
const form = reactive({ start:'', end:'' })
function addDraft () { /* 後で中身実装 */ }
function removeDraft(i){ /* 後で中身実装 */ }
async function submitAll () { /* 後で中身実装 */ }

/* ---------- 監視 ---------- */
watch([dateFrom,dateTo], () => {
  if (isCast.value && castId.value) { loadShifts(); loadSummary(); loadRankings() }
})

/* ---------- 起動 ---------- */
onMounted(async () => {
  if (!user.me) { try { await user.fetchMe?.() } catch {} }
  await resolveCastId()
  await loadAll()
})

/* 表示フォーマット */
const monthlyRows = computed(() => Array.isArray(rankings.value) ? rankings.value : [])
const nextShiftDate  = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_start).format('YYYY/MM/DD') : null
)
const nextShiftStart = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_start).format('HH:mm') : null
)
const nextShiftEnd   = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_end).format('HH:mm') : null
)

/* 伝票クリック（伝票画面が無ければ TODO: 差し替え） */
function openBill(b){
  // 伝票画面が staff-order なら:
  // router.push({ name:'staff-order', query:{ bill: b.id } })
  // いまはダッシュボードで代替 or 無操作
}
function openCustomerBill(id) { /* 後で差し替え */ }
</script>

<template>
  <div class="staff-mypage container-fluid mt-4 pb-5">
    <!-- ===== ヘッダ ===== -->
    <div class="d-flex align-items-center mb-4 gap-4">
      <Avatar :url="avatarUrl" :size="72" class="rounded-circle"/>
      <div>
        <h3 class="mb-1">
          <!-- キャスト名 or スタッフ名の代替 -->
          {{ isCast ? (castInfo?.stage_name || 'キャスト') : (user.me?.username || 'スタッフ') }}
        </h3>
        <p class="mb-0 text-muted" v-if="isCast">
          あなたは現在 <strong v-if="myRank">{{ myRank }} 位</strong><span v-else>圏外</span> です
        </p>
      </div>
    </div>

    <!-- ===== スタッフ向け: 今日のオープン伝票 / お知らせ ===== -->
    <div class="row g-3 mb-4">
      <div class="col-12 col-md-6">
        <div class="card text-bg-light h-100">
          <div class="card-body">
            <h6 class="card-title mb-3">今日のオープン伝票</h6>
            <div v-if="openBills.length" class="list-group">
              <button v-for="b in openBills" :key="b.id"
                      class="list-group-item d-flex justify-content-between align-items-center"
                      @click="openBill(b)">
                <span>#{{ b.id }} / 卓{{ b.table?.number ?? '-' }} / {{ dayjs(b.opened_at).format('HH:mm') }}</span>
                <span class="badge text-bg-primary">開く</span>
              </button>
            </div>
            <p v-else class="text-muted m-0">オープン伝票はありません。</p>
          </div>
        </div>
      </div>

      <div class="col-12 col-md-6">
        <div class="card text-bg-light h-100">
          <div class="card-body">
            <h6 class="card-title mb-3">お店からのお知らせ</h6>
            <ul v-if="notices.length" class="list-group">
              <li v-for="n in notices" :key="n.id" class="list-group-item d-flex justify-content-between">
                <span><strong v-if="n.pinned" class="me-2">📌</strong>{{ n.title || n.message || '(無題)' }}</span>
                <small class="text-muted">{{ dayjs(n.publish_at || n.created_at).format('YYYY/MM/DD') }}</small>
              </li>
            </ul>
            <p v-else class="text-muted m-0">お知らせはありません。</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== ここから下はキャストUI（isCastの時だけ見せる） ===== -->
    <div v-if="isCast">
      <!-- 次シフト & 今日売上 -->
      <div class="row g-3 mb-4">
        <div class="col-6">
          <div class="card text-bg-light">
            <div class="card-body">
              <h6 class="card-title mb-1">次のシフト</h6>
              <p class="card-text fs-5 mb-0">
                <template v-if="nextShift">
                  <span>{{ nextShiftDate }}</span>
                  <span class="ms-2">{{ nextShiftStart }} 〜 {{ nextShiftEnd }}</span>
                </template>
                <span v-else>予定なし</span>
              </p>
            </div>
          </div>
        </div>
        <div class="col-6">
          <div class="card text-bg-light">
            <div class="card-body">
              <h6 class="card-title mb-1">今日の売上</h6>
              <p class="card-text fs-5 mb-0">
                <span v-if="todaySales !== null">{{ yen(todaySales) }}</span>
                <span v-else>–</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- タブ -->
      <nav class="d-flex justify-content-around">
        <a href="#" :class="{ active: activeTab==='apply' }" @click.prevent="setTab('apply')">
          <IconCalendarPlus /><span>シフト申請</span>
        </a>
        <a href="#" :class="{ active: activeTab==='list' }"  @click.prevent="setTab('list')">
          <IconCalendarWeek /><span>シフト一覧</span>
        </a>
        <a href="#" :class="{ active: activeTab==='sales' }" @click.prevent="setTab('sales')">
          <IconRosetteDiscountCheck /><span>売上</span>
        </a>
        <a href="#" :class="{ active: activeTab==='customers' }" @click.prevent="setTab('customers')">
          <IconFaceId /><span>顧客情報</span>
        </a>
      </nav>

      <!-- ▼ シフト申請 -->
      <div v-if="activeTab==='apply'" class="card mb-5">
        <div class="card-header fw-bold">シフト申請</div>
        <div class="card-body bg-white">
          <div class="row g-3 align-items-end">
            <div class="col-md-5">
              <label class="form-label">開始日時</label>
              <input v-model="form.start" type="datetime-local" class="form-control">
            </div>
            <div class="col-md-5">
              <label class="form-label">終了日時</label>
              <input v-model="form.end" type="datetime-local" class="form-control">
            </div>
            <div class="col-md-2 text-end">
              <button class="btn btn-outline-secondary w-100" @click="addDraft">追加</button>
            </div>
          </div>

          <table v-if="draftShifts.length" class="table mb-3">
            <thead><tr><th>#</th><th>開始</th><th>終了</th><th /></tr></thead>
            <tbody>
              <tr v-for="(d,i) in draftShifts" :key="i">
                <td>{{ i+1 }}</td>
                <td>{{ fmt(d.plan_start) }}</td>
                <td>{{ fmt(d.plan_end) }}</td>
                <td><button class="btn" @click="removeDraft(i)"><IconX /></button></td>
              </tr>
            </tbody>
          </table>

          <div class="d-flex justify-content-center mt-5">
            <button class="btn btn-primary" :disabled="!draftShifts.length" @click="submitAll">
              {{ draftShifts.length }} 件まとめて申請
            </button>
          </div>
        </div>
      </div>

      <!-- ▼ 自分のシフト一覧 -->
      <div v-if="activeTab==='list'">
        <h4 class="mt-4 mb-2">シフト一覧</h4>
        <div class="table-responsive">
          <table class="table align-middle text-nowrap">
            <thead class="table-light">
              <tr><th>ID</th><th>予定</th><th>出勤</th><th>退勤</th><th>勤務</th><th>見込給与</th></tr>
            </thead>
            <tbody>
              <tr v-for="s in shifts" :key="s.id">
                <td>{{ s.id }}</td>
                <td>
                  <template v-if="s.plan_start">
                    <div>{{ dayjs(s.plan_start).format('YYYY/MM/DD') }}</div>
                    <div class="fw-bold">
                      {{ dayjs(s.plan_start).format('HH:mm') }} – {{ dayjs(s.plan_end).format('HH:mm') }}
                    </div>
                  </template>
                  <span v-else>–</span>
                </td>
                <td>{{ s.clock_in ? dayjs(s.clock_in).format('HH:mm') : '–' }}</td>
                <td>{{ s.clock_out ? dayjs(s.clock_out).format('HH:mm') : '–' }}</td>
                <td>{{ s.worked_min ? (s.worked_min/60).toFixed(2) + ' h' : '–' }}</td>
                <td>{{ s.payroll_amount ? yen(s.payroll_amount) : '–' }}</td>
              </tr>
              <tr v-if="!shifts.length">
                <td colspan="6" class="text-center text-muted">シフトがありません</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ▼ 売上 -->
      <div v-if="activeTab==='sales'">
        <div class="d-flex align-items-center gap-2 mb-4">
          <input v-model="dateFrom" type="date" class="form-control form-control-sm">
          <span>〜</span>
          <input v-model="dateTo" type="date" class="form-control form-control-sm">
          <button class="" @click="loadSummary"><IconSearch /></button>
        </div>

        <div v-if="salesBreakdown" class="table-responsive">
          <table class="table table-sm text-nowrap align-middle">
            <thead class="table-light">
              <tr>
                <th>シャンパン</th><th>本指名</th><th>場内</th><th>フリー</th>
                <th class="text-end">歩合小計</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{{ yen(salesBreakdown.champ) }}</td>
                <td>{{ yen(salesBreakdown.nom) }}</td>
                <td>{{ yen(salesBreakdown.in) }}</td>
                <td>{{ yen(salesBreakdown.free) }}</td>
                <td class="text-end fw-bold">{{ yen(salesBreakdown.total) }}</td>
              </tr>
            </tbody>
            <tfoot class="table-light fw-bold">
              <tr><td colspan="4" class="text-end">時給小計</td><td class="text-end">{{ yen(salesBreakdown.payroll) }}</td></tr>
              <tr><td colspan="4" class="text-end">支給見込 (歩合+時給)</td><td class="text-end">{{ yen(salesBreakdown.total + salesBreakdown.payroll) }}</td></tr>
            </tfoot>
          </table>
        </div>
        <p v-else class="text-muted d-flex align-items-center justify-content-center" style="min-height:200px;">
          売上はまだありません
        </p>
      </div>

      <!-- ▼ 顧客情報 -->
      <div v-if="activeTab==='customers'">
        <h5>顧客情報</h5>
        <table v-if="customerBills.length" class="table align-middle">
          <thead class="table-light">
            <tr><th>日時</th><th>顧客名</th><th class="text-end">小計</th></tr>
          </thead>
          <tbody>
            <tr v-for="b in customerBills" :key="b.id" role="button" @click="openCustomerBill(b.id)">
              <td>{{ dayjs(b.opened_at).format('YYYY/MM/DD HH:mm') }}</td>
              <td>{{ b.customer_display_name || '-' }}</td>
              <td class="text-end">{{ yen(b.subtotal) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-muted d-flex align-items-center justify-content-center" style="min-height:200px;">
          あなたが担当した顧客情報はまだありません
        </p>
      </div>

      <!-- ランキング -->
      <div class="container mt-4">
        <RankingBlock v-if="monthlyRows.length" label="月間ランキング" :rows="monthlyRows"/>
        <p v-else class="text-muted text-center">集計されていません</p>
      </div>
    </div>
  </div>
</template>

<style>
nav a.active { font-weight: bold; }
</style>
