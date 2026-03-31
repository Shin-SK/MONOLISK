<!-- src/views/CastShiftList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'
import {
  fetchCastShifts,
  createCastShift,
  castCheckIn,
  castCheckOut,
  getBillingCasts
} from '@/api'

const todayISO = dayjs().format('YYYY-MM-DD')
const DAY_LABELS = ['月','火','水','木','金','土','日']
const todayLabel = `${dayjs().format('M月D日')} (${DAY_LABELS[dayjs().isoWeekday?.() - 1] || dayjs().format('ddd')})`

const rows = ref([])
const loading = ref(false)

async function load () {
  loading.value = true
  try {
    const [casts, shifts] = await Promise.all([
      getBillingCasts({ _ts: Date.now() }, { cache: false }),
      fetchCastShifts({ from: todayISO, to: todayISO })
    ])

    const shiftMap = {}
    for (const s of shifts) {
      const cid = s.cast?.id
      if (!cid) continue
      if (!shiftMap[cid]) shiftMap[cid] = []
      shiftMap[cid].push(s)
    }

    rows.value = casts.map(c => {
      const all = shiftMap[c.id] || []
      const working   = all.find(s => s.clock_in && !s.clock_out)
      const scheduled = all.find(s => !s.clock_in && !s.clock_out)
      const done      = all.filter(s => s.clock_out)
      return {
        cast: c,
        activeShift: working || scheduled || null,
        doneCount: done.length,
        status: working ? 'working' : scheduled ? 'scheduled' : done.length ? 'done' : 'none'
      }
    }).sort((a, b) => {
      const order = { working: 0, scheduled: 1, none: 2, done: 3 }
      return (order[a.status] ?? 9) - (order[b.status] ?? 9)
    })
  } finally {
    loading.value = false
  }
}

const fmtTime = d => d ? dayjs(d).format('HH:mm') : ''

async function doCheckIn (row) {
  let shift = row.activeShift
  if (!shift) {
    shift = await createCastShift({ cast_id: row.cast.id })
  }
  await castCheckIn(shift.id)
  await load()
}

async function doCheckOut (row) {
  if (!confirm('退勤しますか？')) return
  await castCheckOut(row.activeShift.id)
  await load()
}

onMounted(load)
</script>

<template>
  <div class="container-fluid py-3">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold mb-0">
        出退勤
        <small class="text-muted fs-6 ms-2">{{ todayLabel }}</small>
      </h4>
      <RouterLink :to="{ name: 'mng-cast-shift-calendar' }" class="btn btn-outline-primary btn-sm">
        シフト一覧
      </RouterLink>
    </div>

    <div class="row g-3">
      <div v-for="row in rows" :key="row.cast.id" class="col-12 col-sm-6 col-lg-4">
        <div
          class="card h-100"
          :class="{
            'border-success border-2': row.status === 'working',
            'border-primary': row.status === 'scheduled',
          }"
        >
          <div class="card-body d-flex align-items-center gap-3">
            <!-- Avatar + Name -->
            <RouterLink :to="{ name: 'mng-cast-shift-detail', params: { id: row.cast.id } }">
              <Avatar :url="row.cast.avatar_url" :alt="row.cast.stage_name" :size="48" />
            </RouterLink>
            <div class="flex-grow-1 min-w-0">
              <div class="fw-bold text-truncate">{{ row.cast.stage_name }}</div>
              <div class="small">
                <template v-if="row.status === 'working'">
                  <span class="badge bg-success">勤務中</span>
                  <span class="text-muted ms-1">{{ fmtTime(row.activeShift.clock_in) }}〜</span>
                </template>
                <template v-else-if="row.status === 'scheduled'">
                  <span class="badge bg-primary">予定</span>
                  <span class="text-muted ms-1">
                    {{ fmtTime(row.activeShift.plan_start) }}–{{ fmtTime(row.activeShift.plan_end) }}
                  </span>
                </template>
                <template v-else-if="row.status === 'done'">
                  <span class="badge bg-secondary">退勤済</span>
                </template>
                <template v-else>
                  <span class="text-muted">シフトなし</span>
                </template>
              </div>
            </div>
            <!-- Action Button -->
            <div class="flex-shrink-0">
              <button
                v-if="row.status === 'none' || row.status === 'scheduled'"
                class="btn btn-primary px-4"
                @click="doCheckIn(row)"
              >出勤</button>
              <button
                v-else-if="row.status === 'working'"
                class="btn btn-danger px-4"
                @click="doCheckOut(row)"
              >退勤</button>
              <span v-else class="text-secondary small">完了</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!rows.length && !loading" class="col-12 text-center text-muted py-5">
        キャストが登録されていません
      </div>
    </div>
  </div>
</template>
