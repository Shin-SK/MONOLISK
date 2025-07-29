<!-- src/views/CastShiftPage.vue -->
<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
import {
  fetchCastShiftHistory,        // 明細
  fetchCastDailySummaries,      // ← 集計
  createCastShift,
  updateCastShift,
  deleteCastShift,
  clearCastAttendance,
} from '@/api'
import { yen } from '@/utils/money'

/* ---------- パラメータ ---------- */
const { params:{ id } } = useRoute()
const castId = Number(id)

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ ---------- */
const rows     = ref([])          // シフト明細
const summary  = ref(null)        // 日次集計 1 行

/* ---------- 新規登録フォーム ---------- */
const newShift = reactive({ start:'', end:'' })

/* ---------- 編集ステート ---------- */
const editing = reactive({
  id: null, plan_start:'', plan_end:'', clock_in:'', clock_out:''
})

/* ---------- stage_name ---------- */
const stageName = computed(() => rows.value[0]?.cast.stage_name || '')

/* ---------- 取得 ---------- */
async function load () {
  /* シフト明細（from / to フィルタ） */
  rows.value = await fetchCastShiftHistory(castId, {
    from: dateFrom.value, to: dateTo.value,
  })

  /* /cast‑daily‑summaries/ → cast は 1 名なので 1 行だけ返る */
  const list = await fetchCastDailySummaries({
    cast : castId,
    from : dateFrom.value,
    to   : dateTo.value,
  })
  summary.value = list[0] ?? null
}

watch([dateFrom, dateTo], load)

/* ---------- 新規シフト登録 ---------- */
async function saveShift () {
  if (!newShift.start || !newShift.end) return alert('開始／終了を入力してください')
  if (dayjs(newShift.start).isAfter(dayjs(newShift.end)))
    return alert('終了は開始より後にしてください')

  await createCastShift({
    cast_id   : castId,
    plan_start: new Date(newShift.start).toISOString(),
    plan_end  : new Date(newShift.end).toISOString(),
  })
  newShift.start = newShift.end = ''
  load()
}

/* ---------- 編集 ---------- */
function startEdit (r) {
  Object.assign(editing, {
    id         : r.id,
    plan_start : r.plan_start ? dayjs(r.plan_start).format('YYYY-MM-DDTHH:mm') : '',
    plan_end   : r.plan_end   ? dayjs(r.plan_end  ).format('YYYY-MM-DDTHH:mm') : '',
    clock_in   : r.clock_in   ? dayjs(r.clock_in ).format('YYYY-MM-DDTHH:mm') : '',
    clock_out  : r.clock_out  ? dayjs(r.clock_out).format('YYYY-MM-DDTHH:mm') : '',
  })
}
const cancelEdit = () => { editing.id = null }

async function saveEdit () {
  const { plan_start:ps, plan_end:pe, clock_in:ci, clock_out:co } = editing
  if (ps && pe && dayjs(ps).isAfter(dayjs(pe)))
    return alert('予定終了は予定開始より後にしてください')
  if (ci && co && dayjs(ci).isAfter(dayjs(co)))
    return alert('退勤は出勤より後にしてください')

  await updateCastShift(editing.id, {
    plan_start: ps ? new Date(ps).toISOString() : null,
    plan_end  : pe ? new Date(pe).toISOString() : null,
    clock_in  : ci ? new Date(ci).toISOString() : null,
    clock_out : co ? new Date(co).toISOString() : null,
  })
  editing.id = null
  load()
}

/* ---------- 個別クリア／削除 ---------- */
async function clearPlan (r) {
  if (!r.plan_start && !r.plan_end) return
  if (confirm('この予定を削除しますか？')) {
    await updateCastShift(r.id, { plan_start:null, plan_end:null })
    load()
  }
}
async function clearAttendance (r) {
  if (!r.clock_in) return
  if (confirm('この出勤・退勤を取り消しますか？')) {
    await clearCastAttendance(r.id)
    load()
  }
}
async function removeShift (r) {
  if (confirm('このシフト（行）を完全に削除します。よろしいですか？')) {
    await deleteCastShift(r.id)
    load()
  }
}

/* ---------- util ---------- */
const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '–'
const h   = (m)=> m ? (m/60).toFixed(2) : '0.00'

onMounted(load)
</script>

<template>
  <div class="container-fluid">

    <!-- ▼ 新規シフト登録 -->
    <div class="card mb-5">
      <div class="card-header fw-bold">シフト登録</div>
      <div class="card-body">
        <div class="row g-3 align-items-end">
          <div class="col-md-5">
            <label class="form-label">開始日時</label>
            <input type="datetime-local" v-model="newShift.start" class="form-control">
          </div>
          <div class="col-md-5">
            <label class="form-label">終了日時</label>
            <input type="datetime-local" v-model="newShift.end" class="form-control">
          </div>
          <div class="col-md-2 text-end">
            <button class="btn btn-primary w-100" @click="saveShift">登録</button>
          </div>
        </div>
      </div>
    </div>
    <!-- ▲ 新規シフト登録 -->

	<div class="d-flex align-items-end gap-2 mb-3">
	<div>
		<label class="form-label">開始日</label>
		<input type="date" v-model="dateFrom" class="form-control">
	</div>
	<div>
		<label class="form-label">終了日</label>
		<input type="date" v-model="dateTo" class="form-control">
	</div>
	<button class="btn btn-primary mb-1" @click="load">再表示</button>
	</div>

    <div v-if="summary" class="alert alert-info">
      この期間の勤務&nbsp;
      <strong>{{ h(summary.worked_min) }} h</strong>／
      時給計&nbsp;<strong>{{ yen(summary.payroll) }}</strong>／
      歩合計&nbsp;<strong>{{ yen(summary.total) }}</strong>／
      <u>支給見込&nbsp;{{ yen(summary.total + summary.payroll) }}</u>
    </div>


    <h2 class="mb-3">シフト履歴 {{ stageName }}</h2>

    <table class="table table-sm align-middle">
      <thead class="table-light">
        <tr>
          <th>ID</th><th>予定</th><th>出勤</th><th>退勤</th>
          <th>勤務</th><th>時給</th><th>給与</th><th class="text-end">操作</th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.id }}</td>

          <!-- 予定 -->
          <td>
            <template v-if="editing.id !== r.id">
              <span v-if="r.plan_start">{{ fmt(r.plan_start) }} – {{ fmt(r.plan_end) }}</span>

              <!-- 予定クリア -->
              <button
                class="btn btn-sm"
                :disabled="!r.plan_start"
                title="予定だけ削除"
                @click="clearPlan(r)"
              >
                <i class="bi bi-x"></i>
              </button>
            </template>

            <template v-else>
              <div class="d-flex gap-2">
                <input type="datetime-local" v-model="editing.plan_start"
                       class="form-control form-control-sm mb-1">
                <input type="datetime-local" v-model="editing.plan_end"
                       class="form-control form-control-sm">
              </div>
            </template>
          </td>

          <!-- 出勤 -->
          <td v-if="editing.id !== r.id">
			{{ fmt(r.clock_in) }}

				<button
				 v-if="r.clock_in"
				class="btn btn-sm"
				:disabled="!r.clock_in"
				title="出勤/退勤をクリア"
				@click="clearAttendance(r)"
				>
				<i class="bi bi-x"></i>
				</button>

          </td>
          <td v-else>
            <input type="datetime-local" v-model="editing.clock_in"
                   class="form-control form-control-sm">
          </td>

          <!-- 退勤 -->
          <td v-if="editing.id !== r.id">{{ fmt(r.clock_out) }}</td>
          <td v-else>
            <input type="datetime-local" v-model="editing.clock_out"
                   class="form-control form-control-sm">
          </td>

          <!-- 勤務 -->
          <td>
            <span v-if="r.worked_min">{{ (r.worked_min/60).toFixed(2) }} h</span>
            <span v-else>–</span>
          </td>

          <!-- 時給／給与 -->
          <td>{{ yen(r.hourly_wage_snap) }}</td>
          <td>{{ r.payroll_amount ? yen(r.payroll_amount) : '–' }}</td>

          <!-- 操作列 -->
          <td class="text-end">
            <template v-if="editing.id !== r.id">
              <button class="btn btn-sm btn-outline-primary me-1"
                      @click="startEdit(r)">
                編集
              </button>

              <!-- 行ごと削除 -->
              <button class="btn btn-sm btn-outline-danger"
                      @click="removeShift(r)">
                削除
              </button>
            </template>

            <template v-else>
              <button class="btn btn-sm btn-success me-1" @click="saveEdit">保存</button>
              <button class="btn btn-sm btn-secondary"   @click="cancelEdit">キャンセル</button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
