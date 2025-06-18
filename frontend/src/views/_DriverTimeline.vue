<!-- src/views/DriverTimeline.vue -->
<script setup>
/* --------------------------------------------------
 * 1. import
 * --------------------------------------------------*/
import { ref, watch, reactive }		 from 'vue'
import FullCalendar		   from '@fullcalendar/vue3'
import timeGridPlugin		 from '@fullcalendar/timegrid'
import interactionPlugin	  from '@fullcalendar/interaction'
import jaLocale			   from '@fullcalendar/core/locales/ja'
import dayjs				  from 'dayjs'
import { useRouter }		  from 'vue-router'
import { api }				from '@/api'

/* --------------------------------------------------
 * 2. 状態
 * --------------------------------------------------*/
const view		  = ref('timeGridDay')	 // 'timeGridDay' | 'timeGridWeek'
const selectedDate  = ref(dayjs())		   // dayjs だと扱いが楽
const events		= ref([])				// ← API から取得して格納
const calRef		= ref(null)			  // FullCalendar の ref
const router		= useRouter()


/* FullCalendar オプション */
const fcOptions = reactive({
  plugins:	   [timeGridPlugin, interactionPlugin],
  initialView:   view.value,
  locale:		jaLocale,
  headerToolbar: false,
  slotMinTime:   '08:00:00',
  slotMaxTime:   '26:00:00',
  nowIndicator:  true,
  events,					   // ref をそのまま
  eventClick: handleEventClick,
})

/* --------------------------------------------------
 * 3. 週ヘッダー用計算ヘルパ
 * --------------------------------------------------*/
const monday = () => selectedDate.value.startOf('week').add(1, 'day') // 月曜
function weekArray () {
  return Array.from({ length: 7 }, (_, i) =>
	monday().add(i, 'day')
  )
}
const weekDays = ref(weekArray())

/* 週送り */
function prevWeek () {
  selectedDate.value = selectedDate.value.subtract(7, 'day')
  weekDays.value	 = weekArray()
}
function nextWeek () {
  selectedDate.value = selectedDate.value.add(7, 'day')
  weekDays.value	 = weekArray()
}

/* --------------------------------------------------
 * 4. イベント取得 & クリック
 * --------------------------------------------------*/
async function loadEvents () {
  const { data } = await api.get('reservations/mine-driver/', {
	params:{ date: selectedDate.value.format('YYYY-MM-DD') }
  })
  events.value = data.map(r => ({
	// FullCalendar の Event オブジェクト仕様
	title: `${r.customer_name} / ${r.status}`,
	start: r.start_at,
	end  : dayjs(r.start_at).add(r.total_time, 'minute').toISOString(),
	extendedProps: { id: r.id }
  }))
}
watch(selectedDate, loadEvents, { immediate:true })

function handleEventClick (info) {
  router.push({ name:'reservation-detail', params:{ id: info.event.extendedProps.id } })
}

/* --------------------------------------------------
 * 5. view 切替
 * --------------------------------------------------*/
function changeView (v){
  view.value = v
  // FullCalendar API 経由でビュー/日付を同時に切替
  const api = calRef.value.getApi()
  api.changeView(v , selectedDate.value.format('YYYY-MM-DD'))
}
</script>

<template>
  <!-- ▼ カスタム週ヘッダー -->
  <div class="timeline-header d-flex align-items-center gap-2 mb-2">
	<button class="btn btn-sm btn-outline-secondary" @click="prevWeek">‹</button>

	<div class="wrap d-flex flex-fill justify-content-between text-center">
	  <div v-for="d in weekDays" :key="d.format('YYYY-MM-DD')"
		   class="weekday flex-fill py-1"
		   :class="{ active: d.isSame(selectedDate,'day') }"
		   @click="selectedDate = d">
		   <div class="weekday__wrap">
			  <div class="date">{{ d.format('ddd') }}</div>
			  <div class="day">{{ d.format('D') }}</div>
		   </div>
	  </div>
	</div>

	<button class="btn btn-sm btn-outline-secondary" @click="nextWeek">›</button>
  </div>

  <!-- ▼ ビュー切替 -->
  <div class="mb-2">
	<button
	  class="btn btn-sm me-1"
	  :class="view==='timeGridDay' ? 'btn-primary' : 'btn-outline-primary'"
	  @click="changeView('timeGridDay')"
	>Day</button>

	<button
	  class="btn btn-sm"
	  :class="view==='timeGridWeek' ? 'btn-primary' : 'btn-outline-primary'"
	  @click="changeView('timeGridWeek')"
	>Week</button>
  </div>

  <!-- ▼ FullCalendar 本体 -->
  <FullCalendar ref="calRef" :options="fcOptions" class="fc-height" />
</template>

<style scoped>
.fc-height{ height:70vh; }

.weekday{
  cursor:pointer; border-radius:.25rem; transition:.2s;
}
</style>
