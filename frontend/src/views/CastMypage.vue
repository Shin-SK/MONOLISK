<!-- src/views/CastMypage.vue -->
<script setup>
/*
 * MVP キャスト用マイページ
 * ---------------------------------------------
 * 機能
 *  1. シフト申請（予定の新規登録）
 *  2. 今月の売上 & 給与サマリ
 *  3. 自分のシフト一覧（期間フィルタ可）
 *  4. 自分のランキング順位
 *  5. 店全体のランキング（再利用出来るようコンポーネント化）
 * ---------------------------------------------
 */
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RankingTable from '@/components/RankingTable.vue'
import dayjs from 'dayjs'

// 🔽 API ラッパ
import {
  createCastShift,
  fetchCastShiftHistory,
  fetchCastDailySummaries,
  fetchCastRankings,
} from '@/api'
import { yen } from '@/utils/money'

/* ---------- パラメータ ---------- */
// MVP: ルートパラメータ ?id= でキャストを決定（将来はログインユーザから取得）
const { params:{ id } } = useRoute()
const castId = Number(id)
if (Number.isNaN(castId)) {
  alert('キャスト ID が不正です');      // MVP 用ガード
  throw new Error('invalid cast id')
}

const router = useRouter()

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- シフト申請フォーム ---------- */
const form = reactive({ start:'', end:'' })
const draftShifts = ref([])


/* ---------- シフトをカートに追加 ---------- */
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

/* ---------- データ ---------- */
const shifts    = ref([])        // 自分のシフト明細
const summary   = ref(null)      // CastDailySummary 1 行
const rankings  = ref([])        // 店全体ランキング（上位10）

/* ---------- util ---------- */
const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '–'
const h   = m => m ? (m/60).toFixed(2) : '0.00'

/* ---------- 取得関数 ---------- */
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

async function loadRankings () {
  rankings.value = await fetchCastRankings({
    from: dateFrom.value,
    to  : dateTo.value,
  })
}

async function loadAll () {
  await Promise.all([loadShifts(), loadSummary(), loadRankings()])
}

/* ---------- シフト新規申請 ---------- */
async function submitAll () {
  if (!draftShifts.value.length) return alert('カートが空です')
  try {
    await Promise.all(
      draftShifts.value.map(s =>
        createCastShift({ cast_id: castId, ...s })
      )
    )
    draftShifts.value = []
    loadShifts()
    alert('申請しました！')
  } catch (e) {
    console.error(e)
    alert('一部登録に失敗しました')
  }
}

function removeDraft(i) { draftShifts.value.splice(i,1) }
/* ---------- 計算 ---------- */
const myRank = computed(() => {
  const idx = rankings.value.findIndex(r => r.cast_id === castId)
  return idx === -1 ? null : idx + 1
})

/* ---------- ウォッチ & 初期ロード ---------- */
watch([dateFrom, dateTo], loadAll)
onMounted(loadAll)
</script>

<template>
  <div class="container-fluid mt-4">

    <!-- ▼ シフト申請 ---------------------------------------------- -->
    <div class="card mb-5">
      <div class="card-header fw-bold">シフト申請</div>
      <div class="card-body">
        <div class="row g-3 align-items-end">
          <div class="col-md-5">
            <label class="form-label">開始日時</label>
            <input type="datetime-local" v-model="form.start" class="form-control">
          </div>
          <div class="col-md-5">
            <label class="form-label">終了日時</label>
            <input type="datetime-local" v-model="form.end" class="form-control">
          </div>
          <div class="col-md-2 text-end">
            <button class="btn btn-outline-secondary w-100" @click="addDraft">追加</button>
          </div>
        </div>
    <!-- カート一覧 -->
     <table v-if="draftShifts.length" class="table table-sm mb-3">
       <thead><tr><th>#</th><th>開始</th><th>終了</th><th></th></tr></thead>
       <tbody>
         <tr v-for="(d,i) in draftShifts" :key="i">
           <td>{{ i+1 }}</td>
           <td>{{ fmt(d.plan_start) }}</td>
           <td>{{ fmt(d.plan_end) }}</td>
           <td>
             <button class="btn btn-sm btn-outline-danger" @click="removeDraft(i)">
               🗑
             </button>
           </td>
         </tr>
       </tbody>
     </table>

    <!-- 一括申請ボタン -->
     <button class="btn btn-primary" @click="submitAll" :disabled="!draftShifts.length">
       {{ draftShifts.length }} 件まとめて申請
     </button>
        <p class="text-muted small mt-2 mb-0">※ MVP では承認フローなしで即登録されます</p>
      </div>
    </div>


    <h4 class="mt-4 mb-2">売上見込</h4>
    <!-- ▼ 期間フィルタ -->
    <div class="d-flex align-items-end gap-2 mb-4">
      <div>
        <label class="form-label">開始日</label>
        <input type="date" v-model="dateFrom" class="form-control" />
      </div>
      <div>
        <label class="form-label">終了日</label>
        <input type="date" v-model="dateTo" class="form-control" />
      </div>
    </div>
    <!-- ▼ 今月のサマリ --------------------------------------------- -->
    <div v-if="summary" class="alert alert-info">
      この期間の勤務 <strong>{{ h(summary.worked_min) }} h</strong> ／
      時給計 <strong>{{ yen(summary.payroll) }}</strong> ／
      歩合計 <strong>{{ yen(summary.total) }}</strong> ／
      <u>支給見込 {{ yen(summary.total + summary.payroll) }}</u>
    </div>

    <!-- ▼ 自分のシフト一覧 ----------------------------------------- -->
    <h4 class="mt-4 mb-2">シフト一覧</h4>
    <table class="table table-sm align-middle">
      <thead class="table-light">
        <tr>
          <th>ID</th><th>予定</th><th>出勤</th><th>退勤</th>
          <th>勤務</th><th>給与</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in shifts" :key="s.id">
          <td>{{ s.id }}</td>
          <td>{{ fmt(s.plan_start) }} – {{ fmt(s.plan_end) }}</td>
          <td>{{ fmt(s.clock_in) }}</td>
          <td>{{ fmt(s.clock_out) }}</td>
          <td>{{ s.worked_min ? (s.worked_min/60).toFixed(2) + ' h' : '–' }}</td>
          <td>{{ s.payroll_amount ? yen(s.payroll_amount) : '–' }}</td>
        </tr>
        <tr v-if="!shifts.length">
          <td colspan="6" class="text-center text-muted">シフトがありません</td>
        </tr>
      </tbody>
    </table>

    <!-- ▼ ランキング ------------------------------------------------- -->
    <h4 class="mt-5 mb-3">ランキング</h4>

    <!-- 自分の順位 -->
    <p v-if="myRank" class="fs-5">
      あなたは現在 <strong class="text-danger">{{ myRank }} 位</strong> です！
    </p>

    <!-- 店舗全体上位10 -->
    <RankingTable :rows="rankings" />
  </div>
</template>