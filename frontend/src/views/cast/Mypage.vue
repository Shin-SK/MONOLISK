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
  fetchStoreNotices
} from '@/api'
import { useUser } from '@/stores/useUser'
import { yen } from '@/utils/money'
import { useAuth } from '@/stores/useAuth'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'

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

/* ---------- シフト月フィルタ ---------- */
const selectedMonth = ref(dayjs().format('YYYY-MM'))

/* ---------- タブ ---------- */
const activeTab = ref('home')
const setTab    = k => (activeTab.value = k)

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
async function loadAll () {
  await Promise.all([ loadCast(), loadShifts(), loadSummary(), loadToday(), loadRankings(), loadNotices(), loadCustomerBills() ])
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
  nextShift.value ? dayjs(nextShift.value.plan_start).format('HH:mm') : null
)

/* ---------- フィルタされたシフト ---------- */
const filteredShifts = computed(() => {
  if (!selectedMonth.value) return shifts.value
  return shifts.value.filter(s => {
    if (!s.plan_start) return false
    return dayjs(s.plan_start).format('YYYY-MM') === selectedMonth.value
  })
})


</script>

<template>
  <div class="cast-mypage mt-4">
    <!-- ===== ヘッダ ===== -->
    <div class="header mb-3">
      <div class="upper mb-4 d-flex align-items-center justify-content-between">
        <h2 class="fs-1 fw-bold ">マイページ</h2>
        <div class="wrap text-muted">{{ dayjs().format('YYYY/MM/DD(ddd)') }}</div>
      </div>
        
      <div class="user-meta d-flex align-items-center justify-content-between">
        <div class="avatars d-flex align-items-center mb-4 gap-4">
          <Avatar :url="avatarUrl" :size="60" class="rounded-circle"/>
          <div class="fs-3 fw-bold m-0">
            {{ castInfo?.stage_name || 'キャスト名' }}
          </div>
        </div>
        <div class="icons">
          <!-- アイコンとかなんか入れるならここに入れてこう -->
        </div>
      </div>
      <div class="bg-white p-4">
        <div v-if="myRank"
          class="mb-0 fs-5 d-flex align-items-center gap-2">
          <IconTrendingUp class="fs-1"/><span class="fs-3">{{ myRank }} 位</span>
        </div>
        <div v-else class="mb-0 fs-5 text-muted">
          これから一緒にがんばりましょう！
        </div>
        <div v-if="todaySales !== null"
          class="wrap d-flex align-items-center gap-2 mt-1">
          <div class="badge bg-secondary text-white">
            今日の売上
          </div>
          <span 
            style="font-size: 2.5rem;"
            class="mb-0 d-flex align-items-center gap-1 fw-bold lh-1">
            {{ yen(todaySales)}}
          </span>
        </div>
        <div v-else class="wrap d-flex align-items-center gap-2 mt-1 text-muted">
          今日もがんばりましょう！
        </div>
      </div>

    </div>


    <div v-if="activeTab === 'home'"
      class="wrap">
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

      <!-- ランキング -->
      <div class="mt-4">
        <div class="fs-5 fw-bold d-flex align-items-center justify-content-center gap-1 mb-1">
          <IconCrown />ランキング
        </div>
        <RankingBlock :rows="monthlyRows" />
      </div>
    </div>


    <!-- ▼ シフト申請 -->
    <div v-if="activeTab === 'apply'"
      class="mb-5"
    >
      <div class="card mb-5">
        <div class="card-header fs-4 fw-bold d-flex align-items-center gap-1">
          <IconCalendarPlus />シフト申請
        </div>
        <div class="card-body bg-white">
          <div class="row g-3 align-items-end">
            <div class="col-md-5">
              <label class="form-label">開始日時</label>
              <input
                v-model="form.start"
                type="datetime-local"
                class="form-control"
              >
            </div>
            <div class="col-md-5">
              <label class="form-label">終了日時</label>
              <input
                v-model="form.end"
                type="datetime-local"
                class="form-control"
              >
            </div>
            <div class="col-md-2 text-end">
              <button
                class="btn btn-outline-secondary w-100"
                @click="addDraft"
              >
                追加
              </button>
            </div>
          </div>

          <table
            v-if="draftShifts.length"
            class="table mb-3"
          >
            <thead><tr><th>#</th><th>開始</th><th>終了</th><th /></tr></thead>
            <tbody>
              <tr
                v-for="(d,i) in draftShifts"
                :key="i"
              >
                <td>{{ i+1 }}</td>
                <td>{{ fmt(d.plan_start) }}</td>
                <td>{{ fmt(d.plan_end) }}</td>
                <td>
                  <button
                    class="btn"
                    @click="removeDraft(i)"
                  >
                    <IconX />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

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
        <h4 class=" fs-4 fw-bold d-flex align-items-center gap-1">
          <IconListTree />シフト一覧
        </h4>
        <div class="search mb-3">
          <input 
            v-model="selectedMonth" 
            type="month" 
            class="form-control bg-white"
            placeholder="月を選択">
        </div>
        <div v-for="s in filteredShifts" :key="s.id"
          class="box p-2 bg-white">
          <div class="time row border-bottom g-2 mb-3 pb-2">
            <div class="col-4 align-items-center d-flex">
              <div class="d-flex align-items-center gap-1">
                <IconClock />
                出勤予定
              </div>
            </div>
            <div class="col-8">
              <div class="text-mute">{{ dayjs(s.plan_start).format('YYYY/MM/DD') }}</div>
              <div class="fw-bold fs-4">
                <span>{{ dayjs(s.plan_start).format('HH:mm') }}</span>〜<span>{{ dayjs(s.plan_end).format('HH:mm') }}</span>
              </div>
            </div>
          </div>
          <div class="info row g-2">
            <div class="in col-4">
              <div class="df-center flex-column">
                <span class="badge bg-secondary">出勤</span>
                <span>{{ s.clock_in ? dayjs(s.clock_in).format('HH:mm') : '–' }}</span>
              </div>
            </div>
            <div class="out col-4">
              <div class="df-center flex-column">
                <span class="badge bg-secondary">退勤</span>
                <span>{{ s.clock_out ? dayjs(s.clock_out).format('HH:mm') : '–' }}</span>
              </div>
            </div>
            <div class="calc col-4">
              <div class="df-center flex-column">
                <span class="badge bg-secondary">勤務時間</span>
                <span>{{ s.worked_min ? (s.worked_min/60).toFixed(2) + ' h' : '–' }}</span>
              </div>
            </div>
          </div>

          

        </div>
        <!-- <div class="table-responsive">
          <table class="table align-middle text-nowrap">
            <thead class="table-light">
              <tr>
                <th>ID</th><th>予定</th><th>出勤</th><th>退勤</th>
                <th>勤務</th><th>見込給与</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="s in shifts"
                :key="s.id"
              >
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
                <td
                  colspan="6"
                  class="text-center text-muted"
                >
                  シフトがありません
                </td>
              </tr>
            </tbody>
          </table>
        </div> -->
      </div>

    </div>

    <div v-if="activeTab==='goals' && castId != null">
      <!-- me は未ロード瞬間があるのでフォールバックを渡す -->
      <CastGoalsPanel :cast-id="castId" :me="me || {}" />
    </div>

    <!-- ▼ 売上 -->
    <div v-if="activeTab === 'sales'">
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
      <h5>顧客情報</h5>

      <table v-if="customerBills.length" class="table align-middle">
        <thead class="table-light">
          <tr><th>日時</th><th>顧客名</th><th class="text-end">小計</th></tr>
        </thead>
        <tbody>
          <tr v-for="b in customerBills" :key="b.id" role="button" @click="openCustomer(b.id)">
            <td>{{ dayjs(b.opened_at).format('YYYY/MM/DD HH:mm') }}</td>
            <td>{{ b.customer_display_name || '-' }}</td>
            <td class="text-end">{{ yen(b.subtotal) }}</td>
          </tr>
        </tbody>
      </table>

      <p v-else
        class="text-muted d-flex align-items-center justify-content-center"
        style="min-height: 200px;">
        あなたが担当した顧客情報はまだありません
      </p>
    </div>

    <CustomerDetailModal
      :bill-id="selectedBillId"
      :show="showCustomerModal"
      @close="closeCustomerModal"
    />
  </div>

    <footer class="position-fixed bottom-0 end-0 start-0 w-100 bg-white py-4">
    <!-- タブ -->
      <nav class="d-flex justify-content-around bg-white">
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'home' }"
          @click="setTab('home')"
        >
          <IconHome :size="40" class="fs-5"/>
          <span class="text-muted">ホーム</span>
        </button>
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'apply' }"
          @click="setTab('apply')"
        >
          <IconCalendarPlus :size="40" class="fs-5"/>
          <span class="text-muted">シフト</span>   
        </button>
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'goals' }"
          @click="setTab('goals')"
        >
          <IconTargetArrow :size="40" class="fs-5"/><span class="text-muted">目標</span>
        </button>
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'sales' }"
          @click="setTab('sales')"
        >
          <IconRosetteDiscountCheck :size="40" class="fs-5"/><span class="text-muted">売上</span>
        </button>
        <button
          class="df-center flex-column"
          :class="{ 'fw-bold': activeTab === 'customers' }"
          @click="setTab('customers')"
        >
          <IconFaceId :size="40" class="fs-5"/><span class="text-muted">顧客</span>
        </button>
      </nav>

    </footer>
</template>

<style>
.avatars img {
  width: 60px !important;
  height: 60px !important;
}
</style>
