<!-- src/components/TimelineView.vue -->
<script setup>
import { ref, watch, reactive }	from 'vue'
import FullCalendar				from '@fullcalendar/vue3'
import timeGridPlugin			from '@fullcalendar/timegrid'
import interactionPlugin		from '@fullcalendar/interaction'
import jaLocale					from '@fullcalendar/core/locales/ja'
import dayjs					from 'dayjs'
import { useRouter }			from 'vue-router'
import { api }					from '@/api'

/* ---------- 状態 ---------- */
const view			= ref('timeGridDay')
const selectedDate	= ref(dayjs())
const events		= ref([])
const calRef		= ref(null)
const router		= useRouter()

/* ---------- FullCalendar オプション ---------- */
const fcOptions = reactive({
	plugins:		 [timeGridPlugin, interactionPlugin],
	initialView:	 view.value,
	locale:			 jaLocale,
	headerToolbar:	 false,
	slotMinTime:	 '08:00:00',
	slotMaxTime:	 '32:00:00',
	dayHeaders:		 false,
	nowIndicator:	 true,
	firstDay:		 1,
	slotLabelFormat:{
		hour:   'numeric',
		minute: '2-digit',
		hour12: false
	},
	events,
	eventClick: handleEventClick,
	dayCellClassNames: arg => (
		arg.date.toISOString().slice(0,10) === selectedDate.value.format('YYYY-MM-DD')
		? ['fc-selected-day']
		: []
	),
})

/* ---------- 週ヘッダー ---------- */
const monday = () => selectedDate.value.startOf('week').add(1,'day')
function weekArray(){
	return Array.from({ length:7 }, (_,i)=> monday().add(i,'day'))
}
const weekDays = ref(weekArray())

/* ---------- 週送り ---------- */
function prevWeek(){
	selectedDate.value = selectedDate.value.subtract(7,'day')
	weekDays.value	 = weekArray()
}
function nextWeek(){
	selectedDate.value = selectedDate.value.add(7,'day')
	weekDays.value	 = weekArray()
}

/* ---------- API ---------- */
async function loadEvents(){
	const { data } = await api.get('reservations/mine-driver/',{
		params:{ date:selectedDate.value.format('YYYY-MM-DD') }
	})
	events.value = data.map(r=>({
		title:`${r.customer_name} / ${r.status}`,
		start:r.start_at,
		end:  dayjs(r.start_at).add(r.total_time,'minute').toISOString(),
		extendedProps:{ id:r.id }
	}))
}
watch(selectedDate, loadEvents, { immediate:true })

function handleEventClick(info){
	router.push({ name:'reservation-detail', params:{ id: info.event.extendedProps.id } })
}

/* ---------- ビュー切替 ---------- */
function changeView(v){
	view.value = v
	const api = calRef.value.getApi()
	api.changeView(v, selectedDate.value.format('YYYY-MM-DD'))
}

/* ---------- 日付クリック ---------- */
function setDate(d){
	selectedDate.value = d
	calRef.value?.getApi().gotoDate(d.format('YYYY-MM-DD'))
}

/* ---------- Today ---------- */
function goToday(){
	const today = dayjs()
	selectedDate.value = today
	weekDays.value	  = weekArray()
	calRef.value?.getApi().gotoDate(today.format('YYYY-MM-DD'))
}
</script>

<template>
	<div class="timeline d-flex flex-column flex-grow-1">
		<!-- ▼ mini 切替＆週ナビ -->
		<div class="mb-2 d-flex align-items-center gap-2 justify-content-end">
			<button
				class="btn btn-sm me-1"
				:class="view==='timeGridDay' ? 'btn-primary' : 'btn-outline-primary'"
				@click="changeView('timeGridDay')"
			>Day</button>

			<button
				class="btn btn-sm me-3"
				:class="view==='timeGridWeek' ? 'btn-primary' : 'btn-outline-primary'"
				@click="changeView('timeGridWeek')"
			>Week</button>

			<button class="btn btn-sm btn-outline-secondary" @click="prevWeek">‹</button>
			<button class="btn btn-sm btn-outline-primary"  @click="goToday">Today</button>
			<button class="btn btn-sm btn-outline-secondary" @click="nextWeek">›</button>
		</div>

		<!-- ▼ カスタム週ヘッダー -->
		<div class="timeline-header mb-2">
			<div class="wrap">
				<div
					v-for="d in weekDays"
					:key="d.format('YYYY-MM-DD')"
					class="weekday"
					@click="setDate(d)"
				>
					<div
						class="weekday__wrap"
						:class="{ active: d.isSame(selectedDate,'day') }"
					>
						<div class="date">{{ d.format('ddd') }}</div>
						<div class="day">{{ d.format('D') }}</div>
					</div>
				</div>
			</div>
		</div>

		<!-- ▼ FullCalendar -->
		<FullCalendar ref="calRef" :options="fcOptions" class="fc-height flex-grow-1"/>
	</div>
</template>

<style scoped>
/* 既存の .timeline, .weekday 系 CSS をそのまま利用 */
</style>
