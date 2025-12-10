<!-- Mypage.vue -->
<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import RankingBlock from '@/components/RankingBlock.vue'
import CastGoalsPanel from '@/components/cast/CastGoalsPanel.vue'
import CustomerDetailModal from '@/components/CustomerDetailModal.vue'
import dayjs from 'dayjs'
import {
  fetchBills,
  createCastShift,
  fetchCastShiftHistory,
  fetchCastDailySummaries,
  fetchCastRankings,
  fetchCastMypage,
  fetchStoreNotices,
  listCastGoals
} from '@/api'
import { useUser } from '@/stores/useUser'
import { yen } from '@/utils/money'
import { useAuth } from '@/stores/useAuth'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'
import CastSidebar from '@/components/sidebar/CastSidebar.vue'
import { openOffcanvas } from '@/utils/bsOffcanvas'

/* ---------- 自分中心：route.id が無ければ me.cast_id を使う ---------- */
const route = useRoute()
const userStore = useUser()
const castId = ref(null)

const auth = useAuth()
const me = computed(() => auth.me)  // ストアが保持する現在ログインユーザー
const { avatarURL } = useProfile()

onMounted(async () => {
  // 二重取得を避けたいなら、未取得時だけ叩く
  if (!me.value) {
    // ストアのメソッド名に合わせてどちらか
    if (typeof auth.fetchMe === 'function') await auth.fetchMe()
    else if (typeof auth.loadMe === 'function') await auth.loadMe()
  }
})

async function resolveCastId() {
  // 1) URLに :id があればそれを優先
  const idParam = Number(route.params.id)
  if (!Number.isNaN(idParam)) { castId.value = idParam; return }

  // 2) なければ /api/me から cast_id を取得
  if (!userStore.me) {
    try { await userStore.fetchMe?.() } catch {}
  }
  if (userStore.me?.cast_id) {
    castId.value = userStore.me.cast_id
    return
  }

  // 3) それでも無ければキャスト権限が無いアカウント
  alert('このアカウントはキャストとして登録されていません。')
  throw new Error('no cast_id')
}

/* ---------- サイドバー ---------- */
function openSidebar(){
  openOffcanvas('#castSidebar')
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
const allCustomerBills = ref([])  // 全顧客用
const latestGoal = ref(null)  // 最新の目標
const goalProgressMap = ref({})  // 目標の進捗

/* ---------- シフト月フィルタ ---------- */
const selectedMonth = ref(dayjs().format('YYYY-MM'))

/* ---------- タブ ---------- */
const activeTab = ref('home')
const setTab    = k => (activeTab.value = k)

/* ---------- 顧客情報タブ ---------- */
const activeCustomerTab = ref('visit-dates')
const setCustomerTab = k => (activeCustomerTab.value = k)

/* ---------- util ---------- */
const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '–'
const h   = m => m ? (m/60).toFixed(2) : '0.00'

/* ---------- データ取得（castId.value を参照） ---------- */
async function loadCast () {
  castInfo.value = await fetchCastMypage(castId.value)
}
async function loadShifts () {
  shifts.value = await fetchCastShiftHistory(castId.value, {
    from: dateFrom.value,
    to  : dateTo.value,
  })
}
async function loadSummary () {
  const list = await fetchCastDailySummaries({
    cast : castId.value,
    from : dateFrom.value,
    to   : dateTo.value,
  })
  summary.value = list[0] ?? null
}
async function loadToday () {
  const list = await fetchCastDailySummaries({
    cast : castId.value,
    from : todayStr,
    to   : todayStr,
  })
  todaySum.value = list[0] ?? null
}
async function loadRankings () {
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
  customerBills.value = (await fetchBills({ cast: castId.value }))
    .filter(b => (b.customer_display_name ?? '').trim().length)
}
async function loadAllCustomerBills () {
  allCustomerBills.value = (await fetchBills({}))
    .filter(b => (b.customer_display_name ?? '').trim().length)
}
async function loadLatestGoal () {
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
async function loadAll () {
  await Promise.all([ loadCast(), loadShifts(), loadSummary(), loadToday(), loadRankings(), loadNotices(), loadCustomerBills(), loadAllCustomerBills(), loadLatestGoal() ])
}

/* ---------- アバター ---------- */
const avatarUrl = computed(() =>
  castInfo.value?.avatar_url || avatarURL.value || ''
)

/* ---------- 計算 ---------- */
const myRank = computed(() => {
  const idx = rankings.value.findIndex(r => r.cast_id === castId.value)
  return idx === -1 ? null : idx + 1
})
const nextShift = computed(() => {
  const now = dayjs()
  return shifts.value
    .filter(s => s.plan_start && dayjs(s.plan_start).isAfter(now))
    .sort((a,b) => dayjs(a.plan_start) - dayjs(b.plan_start))[0] || null
})
const todaySales = computed(() =>
  todaySum.value ? todaySum.value.total + todaySum.value.payroll : null
)
const salesBreakdown = computed(() => summary.value ? {
  champ: summary.value.sales_champ || 0,
  nom  : summary.value.sales_nom   || 0,
  in   : summary.value.sales_in    || 0,
  free : summary.value.sales_free  || 0,
  total: summary.value.total       || 0,
  payroll: summary.value.payroll   || 0,
} : null)

/* ---------- 申請 ---------- */
const form = reactive({ start:'', end:'' })  // 'YYYY-MM-DDTHH:mm'（datetime-local）

function addDraft () {
  // 入力チェック
  const s = String(form.start || '').trim()
  const e = String(form.end   || '').trim()
  if (!s || !e) { alert('開始と終了を入力してください'); return }
  const start = dayjs(s)
  const end   = dayjs(e)
  if (!start.isValid() || !end.isValid()) { alert('日時の形式が不正です'); return }
  if (end.isSameOrBefore(start)) { alert('終了は開始より後にしてください'); return }

  // 下書きに追加（画面表示用：ローカル時刻のまま持つ）
  draftShifts.value.push({
    plan_start: start.toDate(),
    plan_end  : end.toDate(),
  })

  // 入力欄リセット
  form.start = ''
  form.end   = ''
}

function removeDraft(i){
  draftShifts.value.splice(i, 1)
}

const submitting = ref(false)
async function submitAll () {
  if (!draftShifts.value.length) return
  if (!castId.value) { alert('キャストIDが未解決です'); return }
  submitting.value = true
  try {
    // まとめてPOST（store_idはミドルウェアがX-Store-Idから補完する想定）
    for (const d of draftShifts.value) {
      await createCastShift({
        cast_id   : castId.value,
        // APIはISOを想定。datetime-localはローカル時刻なので toISOString() に変換。
        plan_start: dayjs(d.plan_start).toISOString(),
        plan_end  : dayjs(d.plan_end).toISOString(),
      })
    }
    draftShifts.value = []
    // 一覧を最新化
    await loadShifts()
    alert('申請を送信しました')
  } catch (e) {
    console.error('submitAll failed', e)
    alert('申請に失敗しました')
  } finally {
    submitting.value = false
  }
}

// モーダル制御
const showCustomerModal = ref(false)
const selectedBillId    = ref(null)

function openCustomer(id) {
  selectedBillId.value = id
  showCustomerModal.value = true
}
function closeCustomerModal(){
  showCustomerModal.value = false
}


/* ---------- 監視 ---------- */
watch([dateFrom,dateTo], () => { if (castId.value) { loadShifts(); loadSummary(); loadRankings() } })

/* ---------- 起動 ---------- */
onMounted(async () => {
  await resolveCastId()   // ← まず自分の cast_id を決める
  await loadAll()
})

/* ───────── 追加①: 月間ランキングの配列ガード ───────── */
const monthlyRows = computed(() => Array.isArray(rankings.value) ? rankings.value : [])

/* ───────── 追加②: 次シフトの表示用フォーマット ───────── */
const nextShiftDate  = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_start).format('YYYY/MM/DD') : null
)
const nextShiftStart = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_start).format('HH:mm') : null
)
const nextShiftEnd   = computed(() =>
  nextShift.value ? dayjs(nextShift.value.plan_end).format('HH:mm') : null
)

/* ---------- フィルタされたシフト ---------- */
const filteredShifts = computed(() => {
  if (!selectedMonth.value) return shifts.value
  return shifts.value.filter(s => {
    if (!s.plan_start) return false
    return dayjs(s.plan_start).format('YYYY-MM') === selectedMonth.value
  })
})

/* ---------- 顧客ごとの最新来店情報 ---------- */
const customersList = computed(() => {
  // 顧客名でグループ化
  const grouped = {}
  for (const b of customerBills.value) {
    const name = b.customer_display_name || '(名前なし)'
    if (!grouped[name]) {
      grouped[name] = []
    }
    grouped[name].push(b)
  }
  
  // 各顧客の最新来店を取得
  return Object.entries(grouped).map(([name, bills]) => {
    // opened_atで降順ソート（最新が先頭）
    const sorted = bills.sort((a, b) => 
      dayjs(b.opened_at).valueOf() - dayjs(a.opened_at).valueOf()
    )
    const latest = sorted[0]
    
    return {
      name,
      visitCount: bills.length,
      latestVisit: latest.opened_at,
      latestBillId: latest.id,
      latestSubtotal: latest.subtotal,
      // stays から担当キャストを取得
      casts: latest.stays?.map(s => s.cast?.stage_name || s.cast?.name).filter(Boolean) || []
    }
  }).sort((a, b) => dayjs(b.latestVisit).valueOf() - dayjs(a.latestVisit).valueOf())
})

/* ---------- 全顧客の最新来店情報 ---------- */
const allCustomersList = computed(() => {
  // 顧客名でグループ化
  const grouped = {}
  for (const b of allCustomerBills.value) {
    const name = b.customer_display_name || '(名前なし)'
    if (!grouped[name]) {
      grouped[name] = []
    }
    grouped[name].push(b)
  }
  
  // 各顧客の最新来店を取得
  return Object.entries(grouped).map(([name, bills]) => {
    // opened_atで降順ソート（最新が先頭）
    const sorted = bills.sort((a, b) => 
      dayjs(b.opened_at).valueOf() - dayjs(a.opened_at).valueOf()
    )
    const latest = sorted[0]
    
    return {
      name,
      visitCount: bills.length,
      latestVisit: latest.opened_at,
      latestBillId: latest.id,
      latestSubtotal: latest.subtotal,
      // stays から担当キャストを取得
      casts: latest.stays?.map(s => s.cast?.stage_name || s.cast?.name).filter(Boolean) || []
    }
  }).sort((a, b) => dayjs(b.latestVisit).valueOf() - dayjs(a.latestVisit).valueOf())
})

/* ---------- 最新の目標情報を見やすくフォーマット ---------- */
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
    from: dayjs(s).format('YYYY/M/D'),
    to: dayjs(e).format('YYYY/M/D'),
    targetPretty: fmtTarget,
    currentPretty: fmtCurrent,
    percent: pct,
    milestones: goalProgressMap.value[g.id]?.milestones || {}
  }
})

</script>

<template>
  <div class="cast-mypage-page">
    <div class="cast-mypage mt-4">
    <!-- ===== ヘッダ ===== -->
    <div class="header mb-5">
      <div class="upper mb-2 d-flex align-items-center justify-content-between">
        <h2 class="fs-1 fw-bold ">マイページ</h2>
        <div class="wrap text-muted">{{ dayjs().format('YYYY/MM/DD(ddd)') }}</div>
      </div>
        
      <div class="user-meta d-flex align-items-center justify-content-between mb-2">
        <div class="avatars d-flex align-items-center gap-2">
          <Avatar :url="avatarUrl" :size="40" class="rounded-circle"/>
          <div class="fs-4 fw-bold m-0">
            {{ castInfo?.stage_name || 'キャスト名' }}
          </div>
        </div>
        <div class="icons d-flex align-items-center gap-2">
          <button @click="openSidebar"><IconMenuDeep /></button><!-- サイドバー開く -->
        </div>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-12">
          <div class="card p-2">
            <div v-if="latestGoalView" class="d-flex align-items-center justify-content-between">
              <div class="head">
                <div class="d-flex align-items-center gap-1 small fw-bold"><IconTargetArrow />{{ latestGoalView.label }}</div>
              </div>
              <div class="wrap">
                <div class="date">
                  
                  <small class="text-muted d-flex gap-0 mb-1">
                    <IconCalendar />
                    <span>{{ latestGoalView.from }} 〜</span>
                    <span>{{ latestGoalView.to }}</span>
                  </small>
                </div>
                <div class="d-flex align-items-center gap-1 justify-content-end">
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
          <div class="card p-2">
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

        <div class="col-12">
          <div class="card p-2">
            <div class="d-flex align-items-center justify-content-between">
              <div v-if="myRank"
                class="d-flex align-items-center gap-2">
                <IconTrendingUp class="fs-5"/><span class="fs-2 fw-bold">No.{{ myRank }}</span>
              </div>
              <div v-if="todaySales !== null"
                class="wrap df-center gap-2 mt-1">
                <div class="badge bg-secondary text-white">
                  今日の売上
                </div>
                <span
                  class="fs-1 mb-0 d-flex align-items-center gap-1 fw-bold lh-1">
                  {{ yen(todaySales)}}
                </span>
              </div>
              <div v-else class="wrap d-flex align-items-center gap-2 mt-1 text-muted">
                今日もがんばりましょう！
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>


    <div v-if="activeTab === 'home'"
      class="wrap">
      <div class="home-goal">
        <h2 class="fs-5 fw-bold df-center gap-1 mb-2">
          <IconTargetArrow />目標
        </h2>
        <div v-if="latestGoalView" class="card shadow-sm border-0 mb-4">
          <div class="card-header">
            <div class="d-flex align-items-center gap-2 justify-content-between">
              <div class="wrap d-flex align-items-center">
                <IconCalendar class="me-1"/>
                <div class="span">
                  <span class="">{{ latestGoalView.from }}</span>
                  <span> 〜 </span>
                  <span class="">{{ latestGoalView.to }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="card-body">
            <div class="d-flex gap-3 align-items-center mt-2">
              <div class="badge bg-dark text-light">
                {{ latestGoalView.label }}
              </div>
              <div class="d-flex align-items-center gap-1">
                <span class="fs-3 fw-bold lh-1">{{ latestGoalView.currentPretty }}</span>
                <span class="lh-1">/</span>
                <span class="small text-muted lh-1">{{ latestGoalView.targetPretty }}</span>
              </div>
            </div>
            <div class="progress mt-2" style="height:10px;">
              <div
                class="progress-bar"
                role="progressbar"
                :style="{ width: latestGoalView.percent + '%' }"
                :aria-valuenow="latestGoalView.percent" aria-valuemin="0" aria-valuemax="100">
              </div>
            </div>
            <div class="mt-1 small text-end text-muted">
              {{ latestGoalView.percent }}%
            </div>
          </div>
        </div>
        <p v-else class="text-muted">目標はまだ設定されていません</p>
      </div>
      <!-- ランキング -->
      <div class="rank mt-4">
        <div class="fs-5 fw-bold d-flex align-items-center justify-content-center gap-1 mb-1">
          <IconCrown />ランキング
        </div>
        <RankingBlock :rows="monthlyRows" />
      </div>
      <!-- ▼ お店からのお知らせ -->
      <div class="notice mt-5">
        <div class="fs-5 fw-bold d-flex align-items-center justify-content-center gap-1 mb-1"><IconInfoCircle />お知らせ</div>

        <div v-if="notices.length" class="mb-4 bg-white">
          <div
            v-for="n in notices"
            :key="n.id"
            class="d-flex align-items-center justify-content-between p-3"
          >
            <!-- ▼ ここをリンク化して NewsDetail へ -->
            <RouterLink
              :to="{ name: 'news-detail', params: { id: n.id } }"
              class="d-flex flex-column"
            >
              <span class="text-muted small">
                {{ dayjs(n.publish_at || n.created_at).format('YYYY/MM/DD') }}
              </span>
              <span v-if="n.pinned" class="badge bg-warning text-dark me-2">PIN</span>
              <strong>{{ n.title || n.message || '(無題)' }}</strong>
            </RouterLink>
          </div>
        </div>

        <p v-else class="text-muted d-flex align-items-center justify-content-center" style="min-height: 200px;">
          現在お知らせはありません
        </p>
      </div>

    </div>


    <!-- ▼ シフト申請 -->
    <div v-if="activeTab === 'apply'"
      class="mb-5"
    >
      <div class="mb-5">
        <h2 class="fs-5 fw-bold df-center gap-1 mb-2">
          <IconCalendarPlus />シフト申請
        </h2>
        <div class="bg-white p-3">
          <div class="">
            <div class="row g-2">
            <div class="col-3 d-flex align-items-center">
                  <label class="form-label">開始日時</label>
            </div>
            <div class="col-9">
                <input
                  v-model="form.start"
                  type="datetime-local"
                  class="form-control"
                >
            </div>
            <div class="col-3 d-flex align-items-center">
                <label class="form-label">終了日時</label>
            </div>
            <div class="col-9">
                <input
                  v-model="form.end"
                  type="datetime-local"
                  class="form-control"
                >
            </div>
            <div class="col-12 mt-4">
              <button
                class="btn btn-outline-secondary w-100"
                @click="addDraft"
              >
                追加
              </button>
            </div>
          </div>
        </div>

        <div v-if="draftShifts.length" class="mt-3">
          <div v-for="(d,i) in draftShifts"
            class="box p-2 bg-white">
            <div class="time row border-bottom g-2 pb-2">
              <div class="col-4 align-items-center d-flex">
                <div class="d-flex align-items-center gap-1">
                  <IconClock />
                  シフト{{ i+1 }}
                </div>
              </div>
              <div class="col-7">
                <div class="text-muted">{{ dayjs(d.plan_start).format('YYYY/MM/DD') }}</div>
                <div class="fw-bold fs-4">
                  <span>{{ dayjs(d.plan_start).format('HH:mm') }}</span>〜<span>{{ dayjs(d.plan_end).format('HH:mm') }}</span>
                </div>
              </div>
              <div class="col-1 df-center">
                <button
                    @click="removeDraft(i)"
                  >
                    <IconX />
                </button>                
              </div>
            </div>
          </div>
        </div>
        <div class="d-flex justify-content-center mt-3">
          <button
            class="btn btn-primary"
            :disabled="!draftShifts.length || submitting"
            @click="submitAll"
          >
            {{ draftShifts.length }} 件まとめて申請
          </button>
        </div>
      </div>
    </div>

      <div class="wrap">
        <h3 class="fs-5 fw-bold df-center gap-1">
          <IconListTree />シフト一覧
        </h3>
        <div class="search mb-3">
          <input 
            v-model="selectedMonth" 
            type="month" 
            class="form-control bg-white"
            placeholder="月を選択">
        </div>

        <div class="cards-container">
          <div
            v-for="s in filteredShifts"
            :key="s.id"
            class="card shift-card mb-3"
          >
            <div class="card-header d-flex align-items-center gap-2">

                <IconClock />
                <div>{{ dayjs(s.plan_start).format('YYYY/MM/DD') }}</div>
                <div class="wrap fs-4">
                  <span class="fw-bold">{{ dayjs(s.plan_start).format('HH:mm') }}</span>〜<span class="fw-bold">{{ dayjs(s.plan_end).format('HH:mm') }}</span>
                </div>

            </div>

            <div class="card-body">
              <div class="row g-2">
                <div class="col-4 text-center">
                  <div class="badge bg-secondary">出勤</div>
                  <div class="fw-bold mt-1">{{ s.clock_in ? dayjs(s.clock_in).format('HH:mm') : '–' }}</div>
                </div>
                <div class="col-4 text-center">
                  <div class="badge bg-secondary">退勤</div>
                  <div class="fw-bold mt-1">{{ s.clock_out ? dayjs(s.clock_out).format('HH:mm') : '–' }}</div>
                </div>
                <div class="col-4 text-center">
                  <div class="badge bg-secondary">勤務時間</div>
                  <div class="fw-bold mt-1">{{ s.worked_min ? (s.worked_min/60).toFixed(2) + ' h' : '–' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="!filteredShifts.length" class="text-center text-muted py-3">
            シフトがありません
          </div>
        </div>
      </div>

    </div>

    <div v-if="activeTab==='goals' && castId != null">
      <!-- me は未ロード瞬間があるのでフォールバックを渡す -->
      <CastGoalsPanel :cast-id="castId" :me="me || {}" />
    </div>

    <!-- ▼ 売上 -->
    <div v-if="activeTab === 'sales'">
      <h2 class="fs-5 df-center gap-1 fw-bold mb-2"><IconRosetteDiscountCheck />売り上げ一覧</h2>
      <!-- ▼ 売上タブ用：期間フィルタ（スマホ向けにコンパクト） -->
      <div class="row g-2 mb-4 align-items-center">
        <div class="col-5">
          <input
            v-model="dateFrom"
            type="date"
            class="form-control form-control-sm bg-white"
          >
        </div>
        <div class="col-1 d-flex align-items-center justify-content-center">〜</div>
        <div class="col-5">
          <input
            v-model="dateTo"
            type="date"
            class="form-control form-control-sm bg-white"
          >
        </div>
        <button
          class="col-1"
          @click="loadSummary"
        >
          <IconSearch />
        </button>
      </div>

      <!-- <h4 class="mt-5 mb-3">売上 ({{ dateFrom }} 〜 {{ dateTo }})</h4> -->

      <div v-if="salesBreakdown"
        class="table-responsive"
      >
        <table class="table table-sm text-nowrap align-middle">
          <thead class="table-light">
            <tr>
              <th>シャンパン</th>
              <th>本指名</th>
              <th>場内</th>
              <th>フリー</th>
              <th class="text-end">
                歩合小計
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ yen(salesBreakdown.champ) }}</td>
              <td>{{ yen(salesBreakdown.nom) }}</td>
              <td>{{ yen(salesBreakdown.in) }}</td>
              <td>{{ yen(salesBreakdown.free) }}</td>
              <td class="text-end fw-bold">
                {{ yen(salesBreakdown.total) }}
              </td>
            </tr>
          </tbody>
          <tfoot class="table-light fw-bold">
            <tr>
              <td
                colspan="4"
                class="text-end"
              >
                時給小計
              </td>
              <td class="text-end">
                {{ yen(salesBreakdown.payroll) }}
              </td>
            </tr>
            <tr>
              <td
                colspan="4"
                class="text-end"
              >
                支給見込 (歩合+時給)
              </td>
              <td class="text-end">
                {{ yen(salesBreakdown.total + salesBreakdown.payroll) }}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p
        v-else
        class="text-muted d-flex align-items-center justify-content-center"
        style="min-height: 200px;"
      >
        売上はまだありません
      </p>
    </div>

    <!-- ▼ 顧客情報 -->
    <div v-if="activeTab === 'customers'">
      
      <h2 class="df-center gap1 fs-5"><IconFaceId />顧客情報</h2>
      <small class=" df-center mb-4">タップして詳細を表示</small>
      <nav class="row border-bottom g-1 mb-3">
        <div class="col-6">
          <button 
            :class="{ 'border-bottom border-3 border-secondary': activeCustomerTab === 'visit-dates' }"
            @click="setCustomerTab('visit-dates')"
            class="btn flex-grow-1 border-0 rounded-0 w-100 px-0">
            担当したお客様
          </button>
        </div>

        <div class="col-6">
          <button
            :class="{ 'border-bottom border-3 border-secondary': activeCustomerTab === 'customer-info' }"
              @click="setCustomerTab('customer-info')"
              class="btn flex-grow-1 border-0 rounded-0 w-100 px-0">
            お客様一覧
          </button>
        </div>
      </nav>

      <div v-if="activeCustomerTab === 'visit-dates'" class="wrap"><!-- 来店日時 -->
        <div v-if="customerBills.length">
          <div v-for="b in customerBills" :key="b.id"
            @click="openCustomer(b.id)"
            class="card shadow-sm mb-3">
            <div class="card-header fw-bold">
              {{ b.customer_display_name || '-' }}様
            </div>
            <div class="card-body d-flex align-items-center justify-content-between">
              <span>
                {{ dayjs(b.opened_at).format('YYYY/MM/DD HH:mm') }}
              </span>
              <span>
                {{ yen(b.subtotal) }}
              </span>
            </div>
          </div>
        </div>
        <p v-else
          class="text-muted d-flex align-items-center justify-content-center"
          style="min-height: 200px;">
          あなたが担当した顧客情報はまだありません
        </p>
      </div>

      <div v-if="activeCustomerTab === 'customer-info'" class="wrap"><!-- 顧客情報一覧 -->
        <div v-if="allCustomersList.length">
          <div v-for="c in allCustomersList" :key="c.name"
            @click="openCustomer(c.latestBillId)"
            class="card shadow-sm mb-3">
            <div class="card-header d-flex align-items-center justify-content-between">
              <span class="fw-bold">{{ c.name }}様</span>
              <span class="badge bg-secondary">来店{{ c.visitCount }}回</span>
            </div>
            <div class="card-body">
              <div class="row g-2 small">
                <div class="col-6">
                  <div class="text-muted">最終来店</div>
                  <div class="fw-bold">{{ dayjs(c.latestVisit).format('YYYY/MM/DD') }}</div>
                </div>
                <div class="col-6">
                  <div class="text-muted">ご利用金額</div>
                  <div class="fw-bold">{{ yen(c.latestSubtotal) }}</div>
                </div>
                <div v-if="c.casts.length" class="col-12">
                  <div class="text-muted">担当キャスト</div>
                  <div class="fw-bold">{{ c.casts.join(', ') }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <p v-else
          class="text-muted d-flex align-items-center justify-content-center"
          style="min-height: 200px;">
          顧客情報はまだありません
        </p>
      </div>

    </div>

      <CustomerDetailModal
        :bill-id="selectedBillId"
        :show="showCustomerModal"
        @close="closeCustomerModal"
      />
    </div>

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

</template>

<style>
.avatars img {
  width: 60px !important;
  height: 60px !important;
}
</style>
