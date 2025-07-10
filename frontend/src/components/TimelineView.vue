<!-- src/components/TimelineView.vue -->
<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import VueCal from 'vue-cal'
import 'vue-cal/dist/vuecal.css'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useUser } from '@/stores/useUser'

/* ---------- props / emit ---------- */
const props = defineProps({
  apiPath     : { type: String, required: true },
  detailRoute : { type: String, required: true },
  selectedDate: { type: [Date, String], default: undefined }   // 親→子 Date or ISO
})
const emit = defineEmits(['date-change'])

/* ---------- 日付 ---------- */
const selectedDay = ref(dayjs(props.selectedDate).isValid()
                       ? dayjs(props.selectedDate)
                       : dayjs())                       // 常に dayjs

/* props で日付が変わった時同期 */
watch(() => props.selectedDate, d=>{
  if (d && !dayjs(d).isSame(selectedDay.value,'day')){
    selectedDay.value = dayjs(d)
  }
})

/* VueCal ↔ アプリ橋渡し (Date) */
const calDate = computed({
  get: () => selectedDay.value.toDate(),
  set: d  => {
    const next = dayjs(d)
    if (!next.isSame(selectedDay.value,'day')){
      selectedDay.value = next
      emit('date-change', next)           // 親へ dayjs で戻す
    }
  }
})

/* ---------- ★ビューを week で初期化 ---------- */
const view = ref('day')                  // ← ここを 'week' に

/* ---------- ユーザー/ロール判定 ---------- */
const user        = useUser().info
const myDriverId  = user.driver_id ?? user.id
const drvId = d => typeof d.driver==='object' ? d.driver.id : d.driver ?? d.driver_id
const myRoles = rsv =>
  (rsv.reservation_drivers||rsv.drivers||[])
    .filter(d=>drvId(d)===myDriverId).map(d=>d.role)

/* ---------- イベント取得 ---------- */
const events = ref([])
const router = useRouter()

async function loadEvents () {
  let from, to
  if (view.value === 'week') {
    const monday = selectedDay.value.startOf('week').add(1,'day')
    from = monday
    to   = monday.clone().add(6,'day').endOf('day')
  } else {
    from = selectedDay.value.startOf('day')
    to   = from.clone().endOf('day')
  }

  const { data } = await api.get(props.apiPath,{
    params:{ from: from.format('YYYY-MM-DD'), to: to.format('YYYY-MM-DD') }
  })

  const mine = data.filter(r =>
    (r.reservation_drivers||r.drivers||[]).some(d=>drvId(d)===myDriverId)
  )

  events.value = mine.map(r=>{
    const startISO = r.start_at ?? r.start
    if (!startISO) return null
    const minutes  = r.total_time ?? r.courses?.[0]?.minutes ?? 60
    return {
      start : new Date(startISO),
      end   : dayjs(startISO).add(minutes,'minute').toDate(),
      title : `${myRoles(r).join('/') ? `[${myRoles(r).join('/')}] ` : ''}${r.customer_name} / ${r.status}`,
      id    : r.id,
      class : r.status.toLowerCase()
    }
  }).filter(Boolean)
}

onMounted(loadEvents)                      // 初回
watch([selectedDay, view], loadEvents)     // 日付 or ビュー変更時

/* ---------- ナビ操作 ---------- */
function changeView(v){
  if (view.value !== v){
    view.value = v        // :active-view.sync が入っているので UI も即反映
  }
}
function moveWeek(delta){
  selectedDay.value = selectedDay.value.add(delta,'day')
  emit('date-change', selectedDay.value)
}
function goToday(){
  selectedDay.value = dayjs()
  emit('date-change', selectedDay.value)
}
function pickDay(d){                      // 週ヘッダークリック用
  selectedDay.value = d
  emit('date-change', d)
}

/* ---------- 週ヘッダー ---------- */
const weekDays = computed(()=>{
  const monday = selectedDay.value.startOf('week').add(1,'day')
  return [...Array(7)].map((_,i)=>monday.add(i,'day'))
})

function handleEventClick({ event }){
  router.push(`${props.detailRoute}/${event.id}`)
}
</script>


<template>
  <div class="timeline d-flex flex-column flex-grow-1">
    <!-- ナビ -->
    <div class="mb-2 d-flex align-items-center gap-2 justify-content-end">
      <button class="btn btn-sm me-1"
              :class="view==='day' ? 'btn-primary':'btn-outline-primary'"
              @click="changeView('day')">Day</button>
      <button class="btn btn-sm me-3"
              :class="view==='week' ? 'btn-primary':'btn-outline-primary'"
              @click="changeView('week')">Week</button>

      <button class="btn btn-sm btn-outline-secondary" @click="moveWeek(-7)">‹</button>
      <button class="btn btn-sm btn-outline-primary"  @click="goToday">Today</button>
      <button class="btn btn-sm btn-outline-secondary" @click="moveWeek( 7)">›</button>
    </div>

    <!-- カスタム週ヘッダー -->
    <div class="timeline-header mb-2">
      <div class="wrap">
          <div
            v-for="d in weekDays" :key="d.format('YYYY-MM-DD')"
            class="weekday"
            @click="pickDay(d)"
          >
          <div class="weekday__wrap"
               :class="{ active: d.isSame(selectedDay,'day') }">
            <div class="date">{{ d.format('ddd') }}</div>
            <div class="day">{{ d.format('D') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- VueCal 本体 -->
    <VueCal
      v-model:selected-date="calDate"
      :events="events"
      :disable-views="['years','year','month']"
      :active-view.sync="view" 
      :time="true"  
      :time-step="30"
      :on-event-click="handleEventClick"
      hide-view-selector
      now-indicator
      class="flex-grow-1"
    />
  </div>
</template>

<style scoped>

.weekday{cursor:pointer;width:36px;text-align:center}
.weekday__wrap{padding:4px 0;border-radius:4px}
.weekday__wrap.active{background:#0d6efd;color:#fff}
</style>
