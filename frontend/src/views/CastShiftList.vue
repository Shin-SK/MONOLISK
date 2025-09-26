<!-- src/views/CastShiftList.vue (rev4) → 退勤済みは即リストから除外 → 出勤時間“-” 表示 -->
<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import {
  fetchCastShifts,
  createCastShift,
  castCheckIn,
  castCheckOut,
  deleteCastShift,
  getBillingCasts
} from '@/api'

const todayISO = dayjs().format('YYYY-MM-DD')
const rows = ref([])   // [{ cast, shift|null }]

/* ---------- データロード ---------- */
async function load () {
  const [casts, shifts] = await Promise.all([
    getBillingCasts(),
    fetchCastShifts({ date: todayISO })
  ])

  /* ☆ 今日表示する条件 ☆
     1) plan_start が今日 ＆ clock_out が null  (予定 or 勤務中)
     2) clock_in が今日   ＆ clock_out が null  (突発勤務中)
  */
  const active = shifts.filter(s => {
    const plannedToday = s.plan_start && dayjs(s.plan_start).isSame(todayISO, 'day')
    const startedToday = s.clock_in    && dayjs(s.clock_in ).isSame(todayISO, 'day')
    return !s.clock_out && (plannedToday || startedToday)
  })

  const shiftMap = Object.fromEntries(active.map(s => [s.cast.id, s]))

  rows.value = casts
    .map(c => ({ cast: c, shift: shiftMap[c.id] || null }))
    .sort((a, b) => {
      const t1 = a.shift?.plan_start || '9999-12-31'
      const t2 = b.shift?.plan_start || '9999-12-31'
      return t1.localeCompare(t2)
    })
}

/* ---------- util ---------- */
const fmtPlan = s => {
  if (!s || !s.plan_start || !s.plan_end) return '–'
  return `${dayjs(s.plan_start).format('YYYY/MM/DD HH:mm')} – ${dayjs(s.plan_end).format('HH:mm')}`
}

/* ---------- API 操作 ---------- */
async function ensureShift (row) {
  if (!row.shift) {
    row.shift = await createCastShift({
      cast_id : row.cast.id,
      store_id: row.cast.store,
    })
  }
}

async function checkIn (row) {
  await ensureShift(row)
  if (!row.shift.clock_in) {
    await castCheckIn(row.shift.id)
    await load()
  }
}

async function checkOut (row) {
  if (row.shift && !row.shift.clock_out) {
    if (!window.confirm('退勤しますか？')) return
    await castCheckOut(row.shift.id)
    alert('退勤処理が完了しました！')
    await load()    // clock_out が入ったので除外対象に
  }
}

async function removeShift (row) {
  if (row.shift && confirm('本当に削除しますか？')) {
    await deleteCastShift(row.shift.id)
    await load()
  }
}

onMounted(load)
</script>

<template>
  <div class="mt-4">
    <table class="table table-bordered table-hover align-middle table-striped">
      <thead class="table-dark">
        <tr>
          <th>キャスト</th>
          <th>シフト</th>
          <th>出勤時間</th>
          <th class="text-end">
            操作
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.cast.id"
        >
          <td>
            <RouterLink :to="{ name: 'mng-cast-shift-detail', params: { id: row.cast.id } }">
              {{ row.cast.stage_name }}
            </RouterLink>
          </td>

          <td>{{ fmtPlan(row.shift) }}</td>

          <td>
            {{ row.shift?.clock_in ? dayjs(row.shift.clock_in).format('YYYY/MM/DD HH:mm') : '–' }}
          </td>

          <td class="text-end">
            <!-- 出勤 -->
            <button
              v-if="!row.shift?.clock_in"
              class="btn btn-primary"
              @click="checkIn(row)"
            >
              出勤
            </button>

            <!-- 退勤 -->
            <button
              v-else-if="!row.shift?.clock_out"
              class="btn btn-danger"
              @click="checkOut(row)"
            >
              退勤
            </button>

            <!-- 削除 (退勤済み) -->
            <button
              v-else
              class="btn btn-outline-secondary"
              @click="removeShift(row)"
            >
              削除
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td
            colspan="4"
            class="text-center text-muted"
          >
            本日のシフトはありません
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>