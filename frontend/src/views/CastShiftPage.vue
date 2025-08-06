<!-- src/views/CastShiftPage.vue (complete cart版) -->
<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
import {
  fetchCastShiftHistory,
  fetchCastDailySummaries,
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
const rows     = ref([])
const summary  = ref(null)

/* ---------- キャスト名 ---------- */
const stageName = computed(() => rows.value[0]?.cast.stage_name || '')

/* ---------- カート方式フォーム ---------- */
const form = reactive({ start:'', end:'' })
const draftShifts = ref([])

function addDraft(){
  if(!form.start||!form.end) return alert('開始／終了を入力してください')
  if(dayjs(form.start).isAfter(dayjs(form.end))) return alert('終了は開始より後にしてください')
  draftShifts.value.push({
    plan_start:new Date(form.start).toISOString(),
    plan_end  :new Date(form.end ).toISOString(),
  })
  form.start=form.end=''
}
function removeDraft(i){ draftShifts.value.splice(i,1) }
async function submitAll(){
  if(!draftShifts.value.length) return
  await Promise.all(draftShifts.value.map(p=>createCastShift({ cast_id:castId, ...p })))
  draftShifts.value=[]
  await load()
  alert('申請しました！')
}

/* ---------- 編集用 ---------- */
const editing = reactive({ id:null, plan_start:'', plan_end:'', clock_in:'', clock_out:'' })
function startEdit(r){
  Object.assign(editing,{
    id:r.id,
    plan_start:r.plan_start?dayjs(r.plan_start).format('YYYY-MM-DDTHH:mm'):'',
    plan_end  :r.plan_end  ?dayjs(r.plan_end  ).format('YYYY-MM-DDTHH:mm'):'',
    clock_in  :r.clock_in  ?dayjs(r.clock_in ).format('YYYY-MM-DDTHH:mm'):'',
    clock_out :r.clock_out ?dayjs(r.clock_out).format('YYYY-MM-DDTHH:mm'):'',
  })
}
const cancelEdit = ()=>{ editing.id=null }
async function saveEdit(){
  const { plan_start:ps, plan_end:pe, clock_in:ci, clock_out:co } = editing
  if(ps&&pe&&dayjs(ps).isAfter(dayjs(pe))) return alert('予定終了は予定開始より後にしてください')
  if(ci&&co&&dayjs(ci).isAfter(dayjs(co))) return alert('退勤は出勤より後にしてください')
  await updateCastShift(editing.id,{
    plan_start:ps?new Date(ps).toISOString():null,
    plan_end  :pe?new Date(pe).toISOString():null,
    clock_in  :ci?new Date(ci).toISOString():null,
    clock_out :co?new Date(co).toISOString():null,
  })
  editing.id=null
  load()
}

/* ---------- 個別クリア・削除 ---------- */
async function clearPlan(r){
  if(!r.plan_start&&!r.plan_end) return
  if(confirm('この予定を削除しますか？')){
    await updateCastShift(r.id,{ plan_start:null, plan_end:null })
    load()
  }
}
async function clearAttendance(r){
  if(!r.clock_in) return
  if(confirm('この出勤・退勤を取り消しますか？')){
    await clearCastAttendance(r.id)
    load()
  }
}
async function removeShift(r){
  if(confirm('このシフト（行）を完全に削除します。よろしいですか？')){
    await deleteCastShift(r.id)
    load()
  }
}

/* ---------- util ---------- */
const fmt = d=>d?dayjs(d).format('YYYY/MM/DD HH:mm'):'–'
const h   = m=>m?(m/60).toFixed(2):'0.00'

/* ---------- データロード ---------- */
async function load(){
  rows.value = await fetchCastShiftHistory(castId,{ from:dateFrom.value, to:dateTo.value })
  const list = await fetchCastDailySummaries({ cast:castId, from:dateFrom.value, to:dateTo.value })
  summary.value = list[0] ?? null
}
watch([dateFrom,dateTo],load)
onMounted(load)
</script>

<template>
  <div class="container-fluid">
    <h4 class="fw-bold">
      {{ stageName }} さん
    </h4>

    <!-- ▼ シフト申請（カート） -->
    <div class="card mb-5">
      <div class="card-header fw-bold text-center">
        シフト申請
      </div>
      <div class="card-body bg-white">
        <div class="d-flex gap-5">
          <div class="area w-50">
            <div class="d-flex g-3 align-items-end mb-3">
              <table class="table">
                <thead>
                  <tr>
                    <th>開始時刻</th>
                    <th>終了時刻</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <input
                        v-model="form.start"
                        type="datetime-local"
                        class="form-control"
                      >
                    </td>
                    <td>
                      <input
                        v-model="form.end"
                        type="datetime-local"
                        class="form-control"
                      >
                    </td>
                    <td>
                      <button
                        class="btn"
                        @click="addDraft"
                      >
                        <IconCircleDashedPlus />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="area w-50">
            <table class="table">
              <thead>
                <tr><th /><th>開始時刻</th><th>終了時刻</th><th /></tr>
              </thead>
              <tbody>
                <!-- ドラフト行 -->
                <tr
                  v-for="(d,i) in draftShifts"
                  :key="i"
                  class="align-middle"
                >
                  <td>{{ i+1 }}</td>
                  <td>{{ fmt(d.plan_start) || '–' }}</td>
                  <td>{{ fmt(d.plan_end) || '–' }}</td>
                  <td>
                    <button
                      class="btn"
                      @click="removeDraft(i)"
                    >
                      <IconX />
                    </button>
                  </td>
                </tr>

                <!-- 何も無いときはダミー行 -->
                <tr
                  v-if="!draftShifts.length"
                  class="align-middle text-muted"
                >
                  <td /><td>–</td><td>–</td><td />
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="d-flex justify-content-center">
          <button
            class="btn btn-primary"
            :disabled="!draftShifts.length"
            @click="submitAll"
          >
            {{ draftShifts.length }} 件まとめて申請
          </button>
        </div>
      </div>
    </div>

    <!-- ▼ フィルタ -->
    <h3 class="mb-3">
      シフト履歴
    </h3>
    <div class="d-flex align-items-end gap-2 mb-3">
      <div>
        <label class="form-label">開始日</label>
        <input
          v-model="dateFrom"
          type="date"
          class="form-control"
        >
      </div>
      <div>
        <label class="form-label">終了日</label>
        <input
          v-model="dateTo"
          type="date"
          class="form-control"
        >
      </div>
      <button
        class="btn btn-primary mb-1"
        @click="load"
      >
        再表示
      </button>
    </div>

    <!-- ▼ テーブル -->
    <table class="table align-middle">
      <thead class="table-dark">
        <tr>
          <th>ID</th><th>予定</th><th>出勤</th><th>退勤</th>
          <th>勤務</th><th>時給</th><th>給与</th><th class="text-end">
            操作
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in rows"
          :key="r.id"
        >
          <td>{{ r.id }}</td>

          <!-- 予定 -->
          <td>
            <template v-if="editing.id !== r.id">
              <span v-if="r.plan_start">{{ fmt(r.plan_start) }} – {{ fmt(r.plan_end) }}</span>
              <button
                class="btn"
                :disabled="!r.plan_start"
                title="予定削除"
                @click="clearPlan(r)"
              >
                <IconX />
              </button>
            </template>
            <template v-else>
              <div class="d-flex gap-2">
                <input
                  v-model="editing.plan_start"
                  type="datetime-local"
                  class="form-control form-control-sm mb-1"
                >
                <input
                  v-model="editing.plan_end"
                  type="datetime-local"
                  class="form-control form-control-sm"
                >
              </div>
            </template>
          </td>

          <!-- 出勤 -->
          <td v-if="editing.id !== r.id">
            {{ fmt(r.clock_in) }}
            <button
              v-if="r.clock_in"
              class="btn"
              title="出退勤クリア"
              @click="clearAttendance(r)"
            >
              <IconX />
            </button>
          </td>
          <td v-else>
            <input
              v-model="editing.clock_in"
              type="datetime-local"
              class="form-control form-control-sm"
            >
          </td>

          <!-- 退勤 -->
          <td v-if="editing.id !== r.id">
            {{ fmt(r.clock_out) }}
          </td>
          <td v-else>
            <input
              v-model="editing.clock_out"
              type="datetime-local"
              class="form-control form-control-sm"
            >
          </td>

          <!-- 勤務 -->
          <td>{{ r.worked_min ? (r.worked_min/60).toFixed(2)+' h' : '–' }}</td>

          <!-- 時給／給与 -->
          <td>{{ yen(r.hourly_wage_snap) }}</td>
          <td>{{ r.payroll_amount ? yen(r.payroll_amount) : '–' }}</td>

          <!-- 操作 -->
          <td class="text-end">
            <template v-if="editing.id !== r.id">
              <button
                class="btn btn-outline-primary me-2"
                @click="startEdit(r)"
              >
                編集
              </button>
              <button
                class="btn btn-outline-danger"
                @click="removeShift(r)"
              >
                削除
              </button>
            </template>
            <template v-else>
              <button
                class="btn btn-success me-2"
                @click="saveEdit"
              >
                保存
              </button>
              <button
                class="btn btn-secondary"
                @click="cancelEdit"
              >
                キャンセル
              </button>
            </template>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td
            colspan="8"
            class="text-center text-muted"
          >
            シフトがありません
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
