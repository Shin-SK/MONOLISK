<!-- Mypage.vue -->
<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
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
  fetchStoreNotices,
  listCastGoals,
  fetchCustomerMatch,
  fetchCustomerAffinity
} from '@/api'
import { useUser } from '@/stores/useUser'
import { yen } from '@/utils/money'
import { useAuth } from '@/stores/useAuth'
import { useProfile } from '@/composables/useProfile'

/* ---------- 自分中心：route.id が無ければ me.cast_id を使う ---------- */
const route = useRoute()
const userStore = useUser()
const castId = ref(null)

const auth = useAuth()
const me = computed(() => auth.me)  // ストアが保持する現在ログインユーザー

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

/* ---------- 日付 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))
const todayStr = dayjs().format('YYYY-MM-DD')

/* ---------- 状態 ---------- */
const shifts      = ref([])
const summary     = ref(null)
const rankings    = ref([])
const notices     = ref([])
const draftShifts = ref([])
const customerBills = ref([])
const allCustomerBills = ref([])  // 全顧客用
const latestGoal = ref(null)  // 最新の目標
const goalProgressMap = ref({})  // 目標の進捗

// 相性ランキング
const matchLoading = ref(false)
const matchError = ref('')
const matchData = ref(null) // APIのレスポンス全体
const matchRows = computed(() => {
  const results = Array.isArray(matchData.value?.results) ? matchData.value.results : []
  // 名前なし顧客を除外（バックエンド修正が入るまでの保険）
  return results.filter(r => {
    const name = (r.customer?.alias || r.customer?.full_name || r.customer?.display_name || '').trim()
    return name.length > 0
  })
})

// 相性ランキングのフィルタ
const matchSort = ref('spent_30d')
const matchLimit = ref(5)             // 固定5人（MVP）

/* ---------- シフト月フィルタ ---------- */
const selectedMonth = ref(dayjs().format('YYYY-MM'))

/* ---------- タブ ---------- */
const activeTab = ref('home')
const setTab    = k => (activeTab.value = k)

/* ---------- 顧客情報タブ ---------- */
const activeCustomerTab = ref('visit-dates')
const setCustomerTab = k => (activeCustomerTab.value = k)

// 顧客情報一覧の絞り込み
const customerSearch = ref('')
const customerMinVisit = ref(0)
const customerSort = ref('latest') // latest / visits

/* ---------- util ---------- */
const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '–'
const h   = m => m ? (m/60).toFixed(2) : '0.00'

/* ---------- データ取得（castId.value を参照） ---------- */
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
async function loadMatchCustomers() {
  if (!castId.value) return
  matchLoading.value = true
  matchError.value = ''
  try {
    matchData.value = await fetchCustomerMatch({
      cast_id: castId.value,
      sort: matchSort.value,
      limit: matchLimit.value,
    })
  } catch (e) {
    console.error('loadMatchCustomers failed:', e)
    matchError.value = '相性ランキングの取得に失敗しました'
    matchData.value = null
  } finally {
    matchLoading.value = false
  }
}
async function loadAll () {
  await Promise.all([ loadShifts(), loadSummary(), loadRankings(), loadNotices(), loadCustomerBills(), loadAllCustomerBills(), loadLatestGoal() ])
}

/* ---------- 計算 ---------- */
const salesBreakdown = computed(() => summary.value ? {
  champ: summary.value.sales_champ || 0,
  nom  : summary.value.sales_nom   || 0,
  in   : summary.value.sales_in    || 0,
  free : summary.value.sales_free  || 0,
  total: summary.value.total       || 0,
  payroll: summary.value.payroll   || 0,
} : null)

/* ---------- 売上カード用：期間内の最新伝票と区分 ---------- */
const latestBillInRange = computed(() => {
  const list = Array.isArray(customerBills.value) ? [...customerBills.value] : []
  if (!list.length) return null
  const from = dayjs(dateFrom.value).startOf('day')
  const to   = dayjs(dateTo.value).endOf('day')
  const filtered = list.filter(b => {
    const t = dayjs(b.opened_at)
    return t.isValid() && t.isSameOrAfter(from) && t.isSameOrBefore(to)
  })
  const target = (filtered.length ? filtered : list)
    .slice()
    .sort((a,b) => dayjs(b.opened_at).valueOf() - dayjs(a.opened_at).valueOf())[0]
  return target || null
})

const latestBillPosition = computed(() => {
  const b = latestBillInRange.value
  if (!b) return null
  const sid = castId.value
  const stay = (b.stays || []).find(s => (s?.cast?.id === sid) || (s?.cast_id === sid))
  const type = stay?.stay_type
  const label = type === 'nom' ? '本指名'
               : type === 'in' ? '場内'
               : type === 'dohan' ? '同伴'
               : 'フリー'
  const klass = type === 'nom' ? 'badge bg-danger text-white'
               : type === 'in' ? 'badge bg-success text-white'
               : type === 'dohan' ? 'badge bg-secondary text-white'
               : 'badge bg-primary text-white'
  return { label, class: klass }
})

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
const selectedCustomerStats = ref(null)

function findLatestBillIdByDisplayName(name) {
  const all = Array.isArray(allCustomerBills.value) ? allCustomerBills.value : []
  const filtered = all.filter(b => (b.customer_display_name || '') === name)
  if (!filtered.length) return null
  const latest = filtered
    .slice()
    .sort((a,b) => dayjs(b.opened_at).valueOf() - dayjs(a.opened_at).valueOf())[0]
  return latest?.id ?? null
}

function openCustomerByName(name) {
  // 名前が空の場合は何もしない（安全策）
  const trimmedName = (name || '').trim()
  if (!trimmedName) {
    console.warn('openCustomerByName: 名前が空です')
    return
  }
  
  const billId = findLatestBillIdByDisplayName(trimmedName)
  if (!billId) {
    alert('該当する伝票が見つかりませんでした（表示名が一致しない可能性）')
    return
  }
  openCustomer(billId)
}

function openCustomer(id) {
  selectedBillId.value = id
  // 顧客統計（来店回数・直近来店）を算出してモーダルに渡す
  try {
    const findBill = (arr) => (Array.isArray(arr) ? arr.find(b => b.id === id) : null)
    const billObj = findBill(customerBills.value) || findBill(allCustomerBills.value)
    if (billObj) {
      const name = billObj.customer_display_name || ''
      const all = Array.isArray(allCustomerBills.value) ? allCustomerBills.value : []
      const sameCustomerBills = all.filter(b => (b.customer_display_name || '') === name)
      const visitCount = sameCustomerBills.length
      const latestVisit = sameCustomerBills.length
        ? sameCustomerBills
            .map(b => b.opened_at)
            .sort((a,b) => dayjs(b).valueOf() - dayjs(a).valueOf())[0]
        : null
      selectedCustomerStats.value = { name, visit_count: visitCount, last_visit_at: latestVisit }
    } else {
      selectedCustomerStats.value = null
    }
  } catch { selectedCustomerStats.value = null }
  showCustomerModal.value = true
}
function closeCustomerModal(){
  showCustomerModal.value = false
}


/* ---------- 監視 ---------- */
watch([dateFrom,dateTo], () => { if (castId.value) { loadShifts(); loadSummary(); loadRankings() } })
watch(matchSort, () => { loadMatchCustomers() })

/* ---------- 起動 ---------- */
onMounted(async () => {
  await resolveCastId()   // ← まず自分の cast_id を決める
  await loadAll()
  await loadMatchCustomers()
  
  // CastLayoutからのタブ切り替えイベントを受け取る
  window.addEventListener('cast:tab:change', (e) => {
    if (e.detail?.tab) {
      activeTab.value = e.detail.tab
    }
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('cast:tab:change', () => {})
})

/* ───────── 追加①: 月間ランキングの配列ガード ───────── */
const monthlyRows = computed(() => Array.isArray(rankings.value) ? rankings.value : [])

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

/* ---------- 全顧客の最新来店情報（フィルタ付き） ---------- */
const filteredAllCustomersList = computed(() => {
  const q = (customerSearch.value || '').trim().toLowerCase()
  const minV = Number(customerMinVisit.value || 0)

  let list = Array.isArray(allCustomersList.value) ? allCustomersList.value : []

  if (q) {
    list = list.filter(c => (c.name || '').toLowerCase().includes(q))
  }
  if (minV > 0) {
    list = list.filter(c => (c.visitCount || 0) >= minV)
  }

  if (customerSort.value === 'visits') {
    list = list.slice().sort((a,b) => (b.visitCount||0) - (a.visitCount||0))
  } else {
    list = list.slice().sort((a,b) => dayjs(b.latestVisit).valueOf() - dayjs(a.latestVisit).valueOf())
  }
  return list
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
    from: dayjs(s).format('MM/DD'),
    to: dayjs(e).format('MM/DD'),
    targetPretty: fmtTarget,
    currentPretty: fmtCurrent,
    percent: pct,
    milestones: goalProgressMap.value[g.id]?.milestones || {}
  }
})

</script>

<template>
  <div class="cast-mypage-page">
    <div class="cast-mypage mt-3">

    <div v-if="activeTab === 'home'"
      class="wrap">

      <div class="customer-match-section mt-3 mb-5">
        <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-3">
          <IconFaceId />相性チェック顧客</h2>
        <div class="wrap">
        
          <!-- フィルタ（ピル型ボタン） -->
          <div class="row mb-4 g-2">
            <div class="col-6">
              <button
                class="df-center gap-1 w-100 p-1 small"
                @click="matchSort = 'spent_30d'"
                :class="matchSort === 'spent_30d' ? 'badge bg-dark text-white' : 'badge bg-white text-secondary'"
                style="cursor: pointer; border: none;">
                <IconCashBanknoteHeart />直近30日売上
              </button>
            </div>
            <div class="col-6">
              <button
                class="df-center gap-1 w-100 small"
                @click="matchSort = 'spent_total'"
                :class="matchSort === 'spent_total' ? 'badge bg-dark text-white' : 'badge bg-white text-secondary'"
                style="cursor: pointer; border: none;">
                <IconChartBarPopular />総売上
              </button>
            </div>
            <div class="col-4">
              <button
                class="df-center gap-1 small w-100"
                @click="matchSort = 'served_item_count'"
                :class="matchSort === 'served_item_count' ? 'badge bg-dark text-white' : 'badge bg-white text-secondary'"
                style="cursor: pointer; border: none;">
                <IconUserCheck /> 担当頻度
              </button>
            </div>
            <div class="col-4">
              <button
                class="df-center gap-1 small w-100"
                @click="matchSort = 'in_count'"
                :class="matchSort === 'in_count' ? 'badge bg-dark text-white' : 'badge bg-white text-secondary'"
                style="cursor: pointer; border: none;">
                <IconTransferIn />場内回数
              </button>
            </div>
            <div class="col-4">
              <button
                class="df-center gap-1 small w-100"
                @click="matchSort = 'nom_count'"
                :class="matchSort === 'nom_count' ? 'badge bg-dark text-white' : 'badge bg-white text-secondary'"
                style="cursor: pointer; border: none;">
                <IconHandFingerRight />指名回数
              </button>
            </div>
          </div>
          <div v-if="matchLoading" class="text-center text-muted py-3">読み込み中…</div>
          <div v-else-if="matchError" class="alert alert-danger">{{ matchError }}</div>
          <div v-else-if="matchRows.length">
            <div
              v-for="(r, idx) in matchRows"
              :key="r.customer?.id"
              class="card shadow-sm mb-3"
              @click="openCustomerByName(r.customer?.alias || r.customer?.full_name || r.customer?.display_name || '')"
            >
              <div class="card-header d-flex align-items-center justify-content-between">
                <div class="d-flex align-items-center gap-2">
                  <span v-if="idx === 0" class="badge bg-warning text-dark df-center gap-1"><IconFlameFilled style="color:red;" />No.1</span>
                  <span v-else-if="idx === 1" class="badge bg-secondary">No.2</span>
                  <span v-else-if="idx === 2" class="badge bg-secondary">No.3</span>
                  <span class="fw-bold">
                    {{ r.customer?.alias || r.customer?.full_name || r.customer?.display_name || '（名前なし）' }}様
                  </span>
                </div>
                <!-- <span class="badge bg-dark">
                  30日 {{ yen(r.affinity?.spent_with_cast_30d || 0) }}
                </span> -->
              </div>
              <div class="card-body">
                <div class="row g-2 small">
                  <div class="col-6">
                    <div class="text-muted">通算（あなた経由）</div>
                    <div class="fw-bold">{{ yen(r.affinity?.spent_with_cast_total || 0) }}</div>
                  </div>
                  <div class="col-6">
                    <div class="text-muted">担当頻度</div>
                    <div class="fw-bold">{{ r.affinity?.served_item_count || 0 }}回</div>
                  </div>
                  <div class="col-4">
                    <div class="text-muted">場内</div>
                    <div class="fw-bold">{{ r.affinity?.in_count || 0 }}回</div>
                  </div>
                  <div class="col-4">
                    <div class="text-muted">指名</div>
                    <div class="fw-bold">{{ r.affinity?.nom_count || 0 }}回</div>
                  </div>
                  <div class="col-4">
                    <div class="text-muted">最終対応</div>
                    <div class="fw-bold">
                      {{ r.affinity?.last_served_at ? dayjs(r.affinity.last_served_at).format('MM/DD') : '—' }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <p v-else class="text-muted d-flex align-items-center justify-content-center" style="min-height:120px;">
            相性の良いお客様はこれから見つかります。
          </p>
        </div>
      </div>

      <div class="home-goal mb-5">
        <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
          <IconTargetArrow />{{ latestGoalView?.label || '目標' }}
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
      <div class="rank mb-5">
        <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
          <IconCrown />ランキング
        </h2>
        <RankingBlock :rows="monthlyRows" />
      </div>
      <!-- ▼ お店からのお知らせ -->
      <div class="notice mt-5">
        <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
          <IconInfoCircle />お知らせ
        </h2>

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
        <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
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
        <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
          <IconListTree />シフト一覧
        </h2>
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
      <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
        <IconRosetteDiscountCheck />売り上げ一覧</h2>
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

      <div v-if="salesBreakdown"
        class="card mb-4 shadow-sm border-0">
        <div class="card-header d-flex align-items-center justify-content-between">
          <div>
            <template v-if="latestBillInRange">
              {{ dayjs(latestBillInRange.opened_at).format('MM/DD HH:mm') }}
              〜
              {{ latestBillInRange.closed_at
                ? dayjs(latestBillInRange.closed_at).format('MM/DD HH:mm')
                : (latestBillInRange.expected_out
                    ? dayjs(latestBillInRange.expected_out).format('MM/DD HH:mm')
                    : '-')
              }}
            </template>
            <template v-else>-</template>
          </div>
          <div class="price df-center gap-1">
            <span class="badge bg-light text-dark">小計</span>
            <span class="fs-4 fw-bold">{{ yen(salesBreakdown.total) }}</span>
          </div>
        </div>
        <div class="card-body d-flex align-items-start justify-content-between">
          <div class="tables df-center flex-column gap-1">
            <span class="badge bg-light text-dark">卓番号</span>
            <span>{{ latestBillInRange?.table?.number ?? '-' }}</span>
          </div>
          <div class="count df-center flex-column gap-1">
            <span class="badge bg-light text-dark">人数</span>
            <span>{{ latestBillInRange?.guest_count ?? latestBillInRange?.guests ?? '-' }}</span>
          </div>
          <div class="count df-center flex-column gap-1">
            <span class="badge bg-light text-dark">セット数</span>
            <span>{{ latestBillInRange?.set_rounds ?? latestBillInRange?.set_count ?? '-' }}</span>
          </div>
        </div>
        <div class="card-footer d-flex align-items-center justify-content-between border-top">
          <div class="position">
            <span v-if="latestBillPosition" :class="latestBillPosition.class">
              {{ latestBillPosition.label }}
            </span>
          </div>
          <div class="name">{{ latestBillInRange?.customer_display_name || '–' }}</div>
        </div>
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
    
      
      <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
        <IconFaceId />顧客情報一覧</h2>
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

      <!-- 顧客情報一覧（絞り込み機能付き） -->
      <div v-if="activeCustomerTab === 'customer-info'" class="wrap">
        <div class="row g-2 mb-3">
          <div class="col-6">
            <input v-model="customerSearch" class="form-control form-control-sm bg-white" placeholder="名前で検索">
          </div>
          <div class="col-3">
            <select v-model.number="customerMinVisit" class="form-select form-select-sm bg-white">
              <option :value="0">来店条件なし</option>
              <option :value="2">2回〜</option>
              <option :value="3">3回〜</option>
              <option :value="5">5回〜</option>
              <option :value="10">10回〜</option>
            </select>
          </div>
          <div class="col-3">
            <select v-model="customerSort" class="form-select form-select-sm bg-white">
              <option value="latest">最終来店順</option>
              <option value="visits">来店回数順</option>
            </select>
          </div>
        </div>

        <div v-if="filteredAllCustomersList.length">
          <div v-for="c in filteredAllCustomersList" :key="c.name"
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
        :customer-stats="selectedCustomerStats"
        :show="showCustomerModal"
        @close="closeCustomerModal"
      />
    </div>

  </div>




</template>

<style>
.avatars img {
  width: 60px !important;
  height: 60px !important;
}
</style>
