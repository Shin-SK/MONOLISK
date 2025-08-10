<!-- AdminStaffForm.vue – cart UI ver. (CastShiftPage と揃えたフルリプレイス) -->
<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
  fetchStaff,
  updateStaff,
  createStaff,
  deleteStaff,
  fetchStaffShifts,
  createStaffShift,
  patchStaffShift,
  deleteStaffShift,
} from '@/api'
import { getStoreId } from '@/auth'
import { yen } from '@/utils/money'

/* ---------- route / basic ---------- */
const route   = useRoute()
const router  = useRouter()
const isEdit  = !!route.params.id
const staffId = Number(route.params.id)

/* ---------- static options ---------- */
const ROLE_OPTS = [
  { code: 'staff',  label: 'スタッフ' },
  { code: 'submgr', label: '副店長'   },
  { code: 'mgr',    label: '店長'     },
]

/* ------------------------------------------------------------------
 *  プロフィールフォーム
 * ----------------------------------------------------------------*/
const form = reactive({
  username: '', first_name: '', last_name: '',
  hourly_wage: 1300,
  role: 'staff',
  stores: [],
})

async function saveProfile () {
  if (!isEdit && !form.username.trim()) return alert('ユーザー名を入力してください')
  const payload = { ...form }
  const res = isEdit
        ? await updateStaff(staffId, payload)
        : await createStaff(payload)
  if (!isEdit) router.replace({ name: 'settings-staff-form', params: { id: res.id } })
  else router.push({ name: 'settings-staff-list' }) 
}

async function removeProfile () {
  if (!confirm('本当に削除しますか？')) return
  await deleteStaff(staffId)
  router.push({ name: 'settings-staff-list' })
}

/* ------------------------------------------------------------------
 *  シフト管理 – CastShiftPage と同じ「カート」UI
 * ----------------------------------------------------------------*/

/* ---- filters ---- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---- lists ---- */
const rows   = ref([])     // 既存(保存済み)
const drafts = ref([])     // 下書き(未送信)

/* ---- cart form ---- */
const cart = reactive({ start: '', end: '' })
function addDraft () {
  if (!cart.start || !cart.end) return alert('開始／終了を入力してください')
  if (dayjs(cart.start).isAfter(dayjs(cart.end))) return alert('終了は開始より後にしてください')
  drafts.value.push({
    plan_start: new Date(cart.start).toISOString(),
    plan_end  : new Date(cart.end ).toISOString(),
  })
  cart.start = cart.end = ''
}
function removeDraft (i) { drafts.value.splice(i,1) }

async function submitDrafts () {
  if (!drafts.value.length) return
  const storeId = getStoreId() || form.stores[0] || null
  if (!storeId) return alert('店舗IDが取得できません')
  await Promise.all(
    drafts.value.map(d => createStaffShift({
      staff_id: staffId,
      store_id: storeId,
      ...d,
    }))
  )
  drafts.value = []
  await loadShifts()
  alert('シフトを登録しました！')
}

/* ---- edit single row ---- */
const editing = reactive({ id:null, plan_start:'', plan_end:'', clock_in:'', clock_out:'' })
function startEdit (r){
  Object.assign(editing,{
    id: r.id,
    plan_start: r.plan_start ? dayjs(r.plan_start).format('YYYY-MM-DDTHH:mm') : '',
    plan_end  : r.plan_end   ? dayjs(r.plan_end  ).format('YYYY-MM-DDTHH:mm') : '',
    clock_in  : r.clock_in   ? dayjs(r.clock_in ).format('YYYY-MM-DDTHH:mm') : '',
    clock_out : r.clock_out  ? dayjs(r.clock_out).format('YYYY-MM-DDTHH:mm') : '',
  })
}
const cancelEdit = () => { editing.id = null }

async function saveEdit () {
  const { plan_start:ps, plan_end:pe, clock_in:ci, clock_out:co } = editing
  if (ps && pe && dayjs(ps).isAfter(dayjs(pe))) return alert('予定終了は予定開始より後にしてください')
  if (ci && co && dayjs(ci).isAfter(dayjs(co))) return alert('退勤は出勤より後にしてください')
  await patchStaffShift(editing.id, {
    plan_start: ps ? new Date(ps).toISOString() : null,
    plan_end  : pe ? new Date(pe).toISOString() : null,
    clock_in  : ci ? new Date(ci).toISOString() : null,
    clock_out : co ? new Date(co).toISOString() : null,
  })
  editing.id = null
  loadShifts()
}

async function clearPlan (r){
  if (!r.plan_start && !r.plan_end) return
  if (!confirm('この予定を削除しますか？')) return
  await patchStaffShift(r.id,{ plan_start:null, plan_end:null })
  loadShifts()
}
async function clearAttendance (r){
  if (!r.clock_in) return
  if (!confirm('この出勤・退勤を取り消しますか？')) return
  await patchStaffShift(r.id,{ clock_in:null, clock_out:null })
  loadShifts()
}
async function removeShift (r){
  if (!confirm('このシフト（行）を完全に削除します。よろしいですか？')) return
  await deleteStaffShift(r.id)
  loadShifts()
}

/* ---- utils ---- */
const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '–'

/* ---- load ---- */
async function loadProfile(){
  if (!isEdit) return
  const data = await fetchStaff(staffId)
  Object.assign(form, {
    username: data.username,
    first_name: data.first_name,
    last_name : data.last_name,
    hourly_wage: data.hourly_wage ?? 1300,
    stores: data.stores,
    role: data.role_code,
  })
}

async function loadShifts(){
  rows.value = await fetchStaffShifts({
    staff: staffId,
    from : dateFrom.value,
    to   : dateTo.value,
    ordering: '-plan_start',
  })
}

watch([dateFrom,dateTo], loadShifts)
onMounted(async ()=>{
  await loadProfile()
  await loadShifts()
})
</script>

<template>
  <div class="container-fluid">
    <!-- ───────── プロフィール ───────── -->
    <h4 class="fw-bold mb-3">
      {{ form.first_name + form.last_name || form.username }}
    </h4>

    <div class="card mb-5">
      <div class="card-header fw-bold text-center">
        プロフィール
      </div>
      <div class="card-body bg-white">
        <div class="row g-3">
          <div class="col-md-4">
            <label class="form-label">ユーザー名</label>
            <input
              v-model="form.username"
              :readonly="isEdit"
              class="form-control"
            >
          </div>
          <div class="col-md-4">
            <label class="form-label">姓</label>
            <input
              v-model="form.last_name"
              class="form-control"
            >
          </div>
          <div class="col-md-4">
            <label class="form-label">名</label>
            <input
              v-model="form.first_name"
              class="form-control"
            >
          </div>
          <div class="col-md-4">
            <label class="form-label">役職</label>
            <select
              v-model="form.role"
              class="form-select"
            >
              <option
                v-for="r in ROLE_OPTS"
                :key="r.code"
                :value="r.code"
              >
                {{ r.label }}
              </option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label">時給 (円)</label>
            <input
              v-model.number="form.hourly_wage"
              type="number"
              min="0"
              class="form-control"
            >
          </div>
        </div>
        <div class="d-flex gap-2 mt-3">
          <button
            class="btn btn-primary"
            @click="saveProfile"
          >
            保存
          </button>
          <button
            v-if="isEdit"
            class="btn btn-outline-danger"
            @click="removeProfile"
          >
            削除
          </button>
        </div>
      </div>
    </div>

    <!-- ───────── シフト申請 (カート) ───────── -->
    <div class="card mb-5">
      <div class="card-header fw-bold text-center">
        シフト申請
      </div>
      <div class="card-body bg-white">
        <div class="d-flex gap-5 flex-wrap">
          <!-- 入力 -->
          <div
            class="area flex-grow-1"
            style="min-width:280px;max-width:480px;"
          >
            <table class="table table-sm">
              <thead><tr><th>開始</th><th>終了</th><th /></tr></thead>
              <tbody>
                <tr>
                  <td>
                    <input
                      v-model="cart.start"
                      type="datetime-local"
                      class="form-control"
                    >
                  </td>
                  <td>
                    <input
                      v-model="cart.end"
                      type="datetime-local"
                      class="form-control"
                    >
                  </td>
                  <td class="text-center">
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
          <!-- カート内容 -->
          <div
            class="area flex-grow-1"
            style="min-width:280px;max-width:480px;"
          >
            <table class="table table-sm">
              <thead><tr><th>#</th><th>開始</th><th>終了</th><th /></tr></thead>
              <tbody>
                <tr
                  v-for="(d,i) in drafts"
                  :key="i"
                  class="align-middle"
                >
                  <td>{{ i+1 }}</td>
                  <td>{{ fmt(d.plan_start) }}</td>
                  <td>{{ fmt(d.plan_end) }}</td>
                  <td class="text-center">
                    <button
                      class="btn"
                      @click="removeDraft(i)"
                    >
                      <IconX :size="12" />
                    </button>
                  </td>
                </tr>
                <tr
                  v-if="!drafts.length"
                  class="align-middle text-muted"
                >
                  <td /><td>–</td><td>–</td><td />
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="d-flex justify-content-center mt-2">
          <button
            class="btn btn-primary"
            :disabled="!drafts.length"
            @click="submitDrafts"
          >
            {{ drafts.length }} 件まとめて申請
          </button>
        </div>
      </div>
    </div>

    <!-- ───────── シフト履歴 ───────── -->
    <h3 class="mb-3">
      シフト履歴
    </h3>
    <div class="d-flex align-items-end gap-2 mb-3 flex-wrap">
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
        @click="loadShifts"
      >
        再表示
      </button>
    </div>

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
                <IconX :size="12" />
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
              <IconX :size="12" />
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
          <!-- worked -->
          <td>{{ r.worked_min ? (r.worked_min/60).toFixed(2)+' h' : '–' }}</td>
          <!-- pay -->
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
