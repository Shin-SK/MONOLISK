<!-- src/views/CastShiftCalendar.vue -->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import dayjs from 'dayjs'
import isoWeek from 'dayjs/plugin/isoWeek'
import Avatar from '@/components/Avatar.vue'
import { fetchCastShifts, getBillingCasts } from '@/api'

dayjs.extend(isoWeek)

const DAY_LABELS = ['月','火','水','木','金','土','日']

const view = ref('weekly')
const selectedDate = ref(dayjs().format('YYYY-MM-DD'))

const casts  = ref([])
const shifts = ref([])

/* ---------- 週間ヘルパー ---------- */
const weekStart = computed(() => dayjs(selectedDate.value).startOf('isoWeek'))
const weekDays  = computed(() =>
  Array.from({ length: 7 }, (_, i) => weekStart.value.add(i, 'day'))
)

/* ---------- データ取得 ---------- */
async function load () {
  const from = view.value === 'weekly'
    ? weekStart.value.format('YYYY-MM-DD')
    : selectedDate.value
  const to = view.value === 'weekly'
    ? weekStart.value.add(6, 'day').format('YYYY-MM-DD')
    : selectedDate.value

  const [c, s] = await Promise.all([
    getBillingCasts({}, { cache: true }),
    fetchCastShifts({ from, to })
  ])
  casts.value  = c
  shifts.value = s
}

/* ---------- シフト取得ヘルパー ---------- */
function shiftsFor (castId, date) {
  const d = dayjs(date).format('YYYY-MM-DD')
  return shifts.value.filter(s => {
    if (s.cast?.id !== castId) return false
    const planned = s.plan_start && dayjs(s.plan_start).format('YYYY-MM-DD') === d
    const clocked = s.clock_in && !s.plan_start && dayjs(s.clock_in).format('YYYY-MM-DD') === d
    return planned || clocked
  })
}

/* 日別：その日にシフトがあるキャスト一覧 */
const dailyRows = computed(() => {
  return casts.value
    .map(c => ({ cast: c, shifts: shiftsFor(c.id, selectedDate.value) }))
    .filter(r => r.shifts.length > 0)
    .sort((a, b) => {
      const t1 = a.shifts[0]?.plan_start || a.shifts[0]?.clock_in || ''
      const t2 = b.shifts[0]?.plan_start || b.shifts[0]?.clock_in || ''
      return t1.localeCompare(t2)
    })
})

/* 週間：全キャスト表示（休みかどうかがわかるように） */
const weeklyCasts = computed(() => casts.value)

/* ---------- ステータス ---------- */
function cellClass (s) {
  if (s.clock_in && s.clock_out) return 'bg-light text-muted'
  if (s.clock_in) return 'bg-success-subtle text-success-emphasis'
  return 'bg-primary-subtle text-primary-emphasis'
}
function statusBadge (s) {
  if (s.clock_in && s.clock_out) return { label: '退勤済', cls: 'bg-secondary' }
  if (s.clock_in) return { label: '勤務中', cls: 'bg-success' }
  return { label: '予定', cls: 'bg-primary' }
}

/* ---------- フォーマット ---------- */
const fmtTime = d => d ? dayjs(d).format('HH:mm') : ''
function shiftTimeLabel (s) {
  const start = s.plan_start || s.clock_in
  const end   = s.plan_end   || s.clock_out
  if (!start) return '–'
  return dayjs(start).format('H:mm') + (end ? '–' + dayjs(end).format('H:mm') : '〜')
}
const isToday = d => dayjs(d).isSame(dayjs(), 'day')

/* ---------- ナビゲーション ---------- */
function prev () {
  const unit = view.value === 'weekly' ? 7 : 1
  selectedDate.value = dayjs(selectedDate.value).subtract(unit, 'day').format('YYYY-MM-DD')
}
function next () {
  const unit = view.value === 'weekly' ? 7 : 1
  selectedDate.value = dayjs(selectedDate.value).add(unit, 'day').format('YYYY-MM-DD')
}
function goToday () { selectedDate.value = dayjs().format('YYYY-MM-DD') }
function selectDay (d) {
  selectedDate.value = dayjs(d).format('YYYY-MM-DD')
  view.value = 'daily'
}

watch([view, selectedDate], load)
onMounted(load)
</script>

<template>
  <div class="container-fluid py-3">
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="fw-bold mb-0">シフト一覧</h4>
      <RouterLink :to="{ name: 'mng-cast-shift' }" class="btn btn-outline-primary btn-sm">
        出退勤
      </RouterLink>
    </div>

    <!-- Controls -->
    <div class="d-flex align-items-center gap-2 mb-3 flex-wrap">
      <div class="btn-group btn-group-sm">
        <button class="btn" :class="view === 'daily' ? 'btn-dark' : 'btn-outline-dark'" @click="view = 'daily'">日別</button>
        <button class="btn" :class="view === 'weekly' ? 'btn-dark' : 'btn-outline-dark'" @click="view = 'weekly'">週間</button>
      </div>
      <div class="btn-group btn-group-sm">
        <button class="btn btn-outline-secondary" @click="prev">&lsaquo;</button>
        <button class="btn btn-outline-secondary" @click="goToday">今日</button>
        <button class="btn btn-outline-secondary" @click="next">&rsaquo;</button>
      </div>
      <span class="fw-bold">
        <template v-if="view === 'daily'">
          {{ dayjs(selectedDate).format('YYYY年M月D日') }}
          ({{ DAY_LABELS[dayjs(selectedDate).isoWeekday() - 1] }})
        </template>
        <template v-else>
          {{ dayjs(weekStart).format('M/D') }} – {{ dayjs(weekDays[6]).format('M/D') }}
        </template>
      </span>
    </div>

    <!-- ===== Daily View ===== -->
    <div v-if="view === 'daily'">
      <div class="table-responsive">
        <table class="table align-middle mb-0">
          <thead class="table-dark">
            <tr>
              <th>キャスト</th>
              <th>シフト予定</th>
              <th>出勤</th>
              <th>退勤</th>
              <th>ステータス</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in dailyRows" :key="row.cast.id">
              <tr v-for="(s, i) in row.shifts" :key="s.id">
                <td v-if="i === 0" :rowspan="row.shifts.length" class="text-nowrap">
                  <RouterLink
                    :to="{ name: 'mng-cast-shift-detail', params: { id: row.cast.id } }"
                    class="d-flex align-items-center gap-2 text-decoration-none"
                  >
                    <Avatar :url="row.cast.avatar_url" :alt="row.cast.stage_name" :size="32" />
                    <span>{{ row.cast.stage_name }}</span>
                  </RouterLink>
                </td>
                <td class="text-nowrap">
                  <span v-if="s.plan_start">{{ fmtTime(s.plan_start) }} – {{ fmtTime(s.plan_end) }}</span>
                  <span v-else class="text-muted">–</span>
                </td>
                <td class="text-nowrap">{{ fmtTime(s.clock_in) || '–' }}</td>
                <td class="text-nowrap">{{ fmtTime(s.clock_out) || '–' }}</td>
                <td>
                  <span class="badge" :class="statusBadge(s).cls">{{ statusBadge(s).label }}</span>
                </td>
              </tr>
            </template>
            <tr v-if="!dailyRows.length">
              <td colspan="5" class="text-center text-muted py-4">この日のシフトはありません</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ===== Weekly View ===== -->
    <div v-if="view === 'weekly'">
      <div class="table-responsive">
        <table class="table table-bordered align-middle mb-0 weekly-table">
          <thead class="table-dark">
            <tr>
              <th class="sticky-col bg-dark">キャスト</th>
              <th
                v-for="(d, i) in weekDays" :key="i"
                class="text-center"
                :class="{ 'today-col': isToday(d) }"
                style="min-width: 110px; cursor: pointer;"
                @click="selectDay(d)"
              >
                <div>{{ DAY_LABELS[i] }}</div>
                <div :class="{ 'fw-bold': isToday(d) }">{{ dayjs(d).format('M/D') }}</div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cast in weeklyCasts" :key="cast.id">
              <td class="sticky-col text-nowrap">
                <RouterLink
                  :to="{ name: 'mng-cast-shift-detail', params: { id: cast.id } }"
                  class="d-flex align-items-center gap-2 text-decoration-none"
                >
                  <Avatar :url="cast.avatar_url" :alt="cast.stage_name" :size="32" />
                  <span>{{ cast.stage_name }}</span>
                </RouterLink>
              </td>
              <td
                v-for="(d, i) in weekDays" :key="i"
                class="text-center p-2"
                :class="{ 'today-col-body': isToday(d) }"
                style="cursor: pointer;"
                @click="selectDay(d)"
              >
                <div
                  v-for="s in shiftsFor(cast.id, d)" :key="s.id"
                  class="rounded px-2 py-1 mb-1"
                  :class="cellClass(s)"
                >
                  {{ shiftTimeLabel(s) }}
                </div>
                <span v-if="!shiftsFor(cast.id, d).length" class="text-muted">–</span>
              </td>
            </tr>
            <tr v-if="!weeklyCasts.length">
              <td :colspan="8" class="text-center text-muted py-4">この週のシフトはありません</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.weekly-table { font-size: 0.95rem; }
.weekly-table td, .weekly-table th { vertical-align: middle; }
.sticky-col {
  position: sticky;
  left: 0;
  background: #fff;
  z-index: 1;
}
thead .sticky-col {
  z-index: 2;
}
.today-col {
  background: rgba(255, 193, 7, 0.25) !important;
  color: #000 !important;
}
.today-col-body {
  background: rgba(255, 193, 7, 0.08);
}
</style>
