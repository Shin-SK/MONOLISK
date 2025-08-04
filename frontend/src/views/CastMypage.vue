<script setup>
/*
 * MVP キャスト用マイページ
 *  1. シフト申請（予定の新規登録）
 *  2. 今月の売上 & 給与サマリ
 *  3. 自分のシフト一覧（期間フィルタ可）
 *  4. 自分のランキング順位
 *  5. 店全体のランキング
 */
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import RankingBlock from '@/components/RankingBlock.vue'
import dayjs from 'dayjs'
import {
  createCastShift,
  fetchCastShiftHistory,
  fetchCastDailySummaries,
  fetchCastRankings,
  fetchCastMypage,
  fetchStoreNotices
} from '@/api'
import { yen } from '@/utils/money'

/* ---------- パラメータ ---------- */
const { params:{ id } } = useRoute()
const castId = Number(id)
if (Number.isNaN(castId)) {
  alert('キャスト ID が不正です')
  throw new Error('invalid cast id')
}

/* ---------- 日付 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))
const todayStr = dayjs().format('YYYY-MM-DD')

/* ---------- 状態 ---------- */
const castInfo    = ref(null)
const shifts      = ref([])            // 自分のシフト一覧
const summary     = ref(null)          // 期間サマリ（売上）
const todaySum    = ref(null)          // 今日サマリ
const rankings    = ref([])            // 店全体ランキング
const monthlyRows = computed(() => rankings.value)
const notices     = ref([])            // 店舗お知らせ
const draftShifts = ref([])            // シフト申請カート

/* ---------- タブ ---------- */
const activeTab = ref(null)
const setTab    = k => (activeTab.value = k)

/* ---------- 申請フォーム ---------- */
const form = reactive({ start:'', end:'' })

/* ---------- util ---------- */
const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '–'
const h   = m => m ? (m/60).toFixed(2) : '0.00'

/* ---------- データ取得 ---------- */
async function loadCast () {
  castInfo.value = await fetchCastMypage(castId)
}
async function loadShifts () {
  shifts.value = await fetchCastShiftHistory(castId, {
    from: dateFrom.value,
    to  : dateTo.value,
  })
}
async function loadSummary () {
  const list = await fetchCastDailySummaries({
    cast : castId,
    from : dateFrom.value,
    to   : dateTo.value,
  })
  summary.value = list[0] ?? null
}
async function loadToday () {
  const list = await fetchCastDailySummaries({
    cast : castId,
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
  notices.value = await fetchStoreNotices()
}
async function loadAll () {
  await Promise.all([
    loadCast(), loadShifts(),
    loadSummary(), loadToday(),
    loadRankings(), loadNotices()
  ])
}

/* ---------- 計算 ---------- */
const myRank = computed(() => {
  const idx = rankings.value.findIndex(r => r.cast_id === castId)
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

/* ---------- 売上ブレイクダウン ---------- */
const salesBreakdown = computed(() => summary.value ? {
  champ: summary.value.sales_champ || 0,
  nom  : summary.value.sales_nom   || 0,
  in   : summary.value.sales_in    || 0,
  free : summary.value.sales_free  || 0,
  total: summary.value.total       || 0,
  payroll: summary.value.payroll   || 0,
} : null)

/* ---------- シフト申請 ---------- */
function addDraft () {
  if (!form.start || !form.end) return alert('開始／終了を入力してください')
  if (dayjs(form.start).isAfter(dayjs(form.end)))
    return alert('終了は開始より後にしてください')
  draftShifts.value.push({
    plan_start: new Date(form.start).toISOString(),
    plan_end  : new Date(form.end ).toISOString(),
  })
  form.start = form.end = ''
}
function removeDraft(i){ draftShifts.value.splice(i,1) }
async function submitAll () {
  if (!draftShifts.value.length) return alert('カートが空です')
  try{
    await Promise.all(
      draftShifts.value.map(s => createCastShift({ cast_id: castId, ...s }))
    )
    draftShifts.value = []
    await loadShifts()
    alert('申請しました！')
  }catch(e){
    console.error(e)
    alert('一部登録に失敗しました')
  }
}

/* ---------- 次シフト日時フォーマット ---------- */
const nextShiftDate  = computed(() => nextShift.value ? dayjs(nextShift.value.plan_start).format('YYYY/MM/DD') : null)
const nextShiftStart = computed(() => nextShift.value ? dayjs(nextShift.value.plan_start).format('HH:mm') : null)
const nextShiftEnd   = computed(() => nextShift.value ? dayjs(nextShift.value.plan_end  ).format('HH:mm') : null)

/* ---------- ウォッチ ---------- */
watch([dateFrom,dateTo], () => { loadShifts(); loadSummary(); loadRankings() })
onMounted(loadAll)
</script>

<template>
  <div class="cast-mypage container-fluid mt-4 pb-5">
    <!-- ===== ヘッダ ===== -->
    <div class="d-flex align-items-center mb-4 gap-4">
      <img v-if="castInfo?.avatar_url" :src="castInfo.avatar_url" alt="avatar"
           class="rounded-circle" style="width:72px;height:72px;object-fit:cover" />
      <div>
        <h3 class="mb-1">{{ castInfo?.stage_name || 'キャスト名' }}</h3>
        <p class="mb-0 text-muted">
          あなたは現在 <strong v-if="myRank">{{ myRank }} 位</strong>
          <span v-else>圏外</span> です
        </p>
      </div>
    </div>

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
      <a href="#" :class="{ active: activeTab === 'apply' }" @click.prevent="setTab('apply')">
        <i class="bi bi-calendar-plus"></i><span>シフト申請</span>
      </a>
      <a href="#" :class="{ active: activeTab === 'list' }" @click.prevent="setTab('list')">
        <i class="bi bi-table"></i><span>シフト一覧</span>
      </a>
      <a href="#" :class="{ active: activeTab === 'sales' }" @click.prevent="setTab('sales')">
        <i class="bi bi-currency-yen"></i><span>売上</span>
      </a>
      <a href="#" :class="{ active: activeTab === 'customers' }" @click.prevent="setTab('customers')">
        <i class="bi bi-people"></i><span>顧客情報</span>
      </a>
    </nav>

    <!-- ▼ シフト申請 -->
    <div v-if="activeTab === 'apply'" class="card mb-5">
      <div class="card-header fw-bold">シフト申請</div>
      <div class="card-body bg-white">
        <div class="row g-3 align-items-end">
          <div class="col-md-5">
            <label class="form-label">開始日時</label>
            <input type="datetime-local" v-model="form.start" class="form-control" />
          </div>
          <div class="col-md-5">
            <label class="form-label">終了日時</label>
            <input type="datetime-local" v-model="form.end" class="form-control" />
          </div>
          <div class="col-md-2 text-end">
            <button class="btn btn-outline-secondary w-100" @click="addDraft">追加</button>
          </div>
        </div>

        <table v-if="draftShifts.length" class="table mb-3">
          <thead><tr><th>#</th><th>開始</th><th>終了</th><th></th></tr></thead>
          <tbody>
            <tr v-for="(d,i) in draftShifts" :key="i">
              <td>{{ i+1 }}</td>
              <td>{{ fmt(d.plan_start) }}</td>
              <td>{{ fmt(d.plan_end) }}</td>
              <td>
                <button class="btn" @click="removeDraft(i)"><i class="bi bi-x"></i></button>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="d-flex justify-content-center mt-5">
          <button class="btn btn-primary" @click="submitAll" :disabled="!draftShifts.length">
            {{ draftShifts.length }} 件まとめて申請
          </button>
        </div>
      </div>
    </div>

    <!-- ▼ 自分のシフト一覧 -->
    <div v-if="activeTab === 'list'">
      <h4 class="mt-4 mb-2">シフト一覧</h4>
      <div class="table-responsive">
        <table class="table align-middle text-nowrap">
          <thead class="table-light">
            <tr>
              <th>ID</th><th>予定</th><th>出勤</th><th>退勤</th>
              <th>勤務</th><th>見込給与</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in shifts" :key="s.id">
              <td>{{ s.id }}</td>
              <!-- ★ 予定を 2 行表記 (日付 / 時間帯) -->
              <td>
                <template v-if="s.plan_start">
                  <div>{{ dayjs(s.plan_start).format('YYYY/MM/DD') }}</div>
                  <div class="fw-bold">{{ dayjs(s.plan_start).format('HH:mm') }} – {{ dayjs(s.plan_end).format('HH:mm') }}</div>
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
        <div class="d-flex justify-content-center">
          <button class="btn btn-outline-primary" @click="setTab('apply')">
            シフト申請
          </button>
        </div>
      </div>
    </div>

    <!-- ▼ 売上 -->
    <div v-if="activeTab === 'sales'">
      <!-- ▼ 売上タブ用：期間フィルタ（スマホ向けにコンパクト） -->
      <div class="d-flex align-items-center gap-2 mb-4">
        <div>
          <input type="date" v-model="dateFrom"
                class="form-control form-control-sm" />
        </div>
        <div>
          〜
        </div>
        <div>
          <input type="date" v-model="dateTo"
                class="form-control form-control-sm" />
        </div>
        <!-- v-model 変更で自動再読込しているなら @click は不要。
            明示的に押して更新したいなら loadSummary() を呼ぶ -->
        <button class=""
                @click="loadSummary">
          <i class="bi bi-search"></i>
        </button>
      </div>

      <!-- <h4 class="mt-5 mb-3">売上 ({{ dateFrom }} 〜 {{ dateTo }})</h4> -->

      <div v-if="salesBreakdown" class="table-responsive">
        <table class="table table-sm text-nowrap align-middle">
          <thead class="table-light">
            <tr>
              <th>シャンパン</th>
              <th>本指名</th>
              <th>場内</th>
              <th>フリー</th>
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
            <tr>
              <td colspan="4" class="text-end">時給小計</td>
              <td class="text-end">{{ yen(salesBreakdown.payroll) }}</td>
            </tr>
            <tr>
              <td colspan="4" class="text-end">支給見込 (歩合+時給)</td>
              <td class="text-end">{{ yen(salesBreakdown.total + salesBreakdown.payroll) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p v-else class="text-muted">売上はまだありません</p>
    </div>

    <!-- ▼ 売上 -->
    <div v-if="activeTab === 'customers'">
      <h4 class="mt-5 mb-3">顧客情報</h4>
      <p class="text-muted">顧客情報はまだありません</p>
    </div>

    <!-- ▼ 顧客情報 -->
    <div class="notice mt-5">
      <h5>お店からのお知らせ</h5>
      <ul v-if="notices.length" class="list-group mb-4">
        <li v-for="n in notices" :key="n.id" class="list-group-item">
          {{ n.message }}
          <span class="text-muted small ms-2">{{ dayjs(n.created_at).format('YYYY/MM/DD') }}</span>
        </li>
      </ul>
      <p v-else class="text-muted d-flex align-items-center justify-content-center" style="min-height: 200px;">現在お知らせはありません</p>
    </div>

    <!-- ランキング -->
    <div class="container mt-4">
      <RankingBlock
        v-if="monthlyRows.length"
        label="月間ランキング"
        :rows="monthlyRows"
      />
      <p v-else class="text-muted text-center">集計されていません</p>
    </div>
  </div>
</template>

<style>
nav a.active { font-weight: bold; }
</style>
