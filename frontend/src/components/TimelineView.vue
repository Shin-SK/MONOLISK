<!-- src/components/TimelineView.vue -->
<script setup>
import { ref, watch, reactive, computed } from 'vue'
import FullCalendar             from '@fullcalendar/vue3'
import timeGridPlugin           from '@fullcalendar/timegrid'
import interactionPlugin        from '@fullcalendar/interaction'
import jaLocale                 from '@fullcalendar/core/locales/ja'
import dayjs                    from 'dayjs'
import { useRouter }            from 'vue-router'
import { api }                  from '@/api'
import { useUser } from '@/stores/useUser'

/* ---------- props ---------- */
const props = defineProps({
  apiPath:      { type:String, required:true },   // 例 'reservations/mine-driver/'
  detailRoute:  { type:String, required:true },   // 例 '/driver/reservations'
  selectedDate: Object                            // 親 ⇔ 子 同期用
})
const emit = defineEmits(['date-change'])         // 親へ日付変更通知

/* ---------- 基本状態 ---------- */
const view          = ref('timeGridDay')
const selectedDate  = ref(props.selectedDate ?? dayjs())   // 内部でも保持
watch(() => props.selectedDate, d => { if (d) selectedDate.value = d })

const events  = ref([])
const calRef  = ref(null)
const router  = useRouter()


/* ----- 自分の driverId を取る --------------------------------- */
const user = useUser().info
// ① driver_id を優先。無ければユーザーIDを fallback に
const myDriverId = user.driver_id ?? user.id
if (!myDriverId) console.warn('driver_id がありません')

/* ----- driver オブジェクト → id を吸い出すヘルパ ------------ */
const drvId = d =>
  typeof d.driver === 'object'
    ? d.driver.id           // {driver:{id:…}}
    : d.driver ?? d.driver_id ?? d.driverId ?? null
function myRoles (rsv) {
  return (rsv.reservation_drivers || rsv.drivers || [])
           .filter(d => drvId(d) === myDriverId)
           .map(d => d.role)         // 例 ['PU','DO']
}

/* ---------- FullCalendar オプション ---------- */
const fcOptions = reactive({
  plugins:          [timeGridPlugin, interactionPlugin],
  initialView:      view.value,
  locale:           jaLocale,
  headerToolbar:    false,
  slotMinTime:      '08:00:00',
  slotMaxTime:      '32:00:00',
  dayHeaders:       false,
  nowIndicator:     true,
  firstDay:         1,
  slotLabelFormat:  { hour:'numeric', minute:'2-digit', hour12:false },
  events,
  eventClick: handleEventClick,
  dayCellClassNames: arg =>
    arg.date.toISOString().slice(0,10) === selectedDate.value.format('YYYY-MM-DD')
      ? ['fc-selected-day'] : [],
})

/* ---------- 週ヘッダー ---------- */
const monday = () => selectedDate.value.startOf('week').add(1,'day')
function makeWeek(){ return Array.from({length:7},(_,i)=>monday().add(i,'day')) }
const weekDays = ref(makeWeek())

/* ---------- API  ---------- */
async function loadEvents(){
  const { data } = await api.get(props.apiPath,{
    params:{ date:selectedDate.value.format('YYYY-MM-DD') }
  })
  /* ② 自分が関与する予約だけ残す ---------------------------- */
  const mine = data.filter(r =>
    (r.reservation_drivers || r.drivers || [])
      .some(d => drvId(d) === myDriverId)
  )

  events.value = 
    /* ② タイトルにロールを付ける ---------------------------- */
 events.value = mine.map(r => {
   const roleTag = myRoles(r).join('/')   // 'PU' / 'DO' / 'PU/DO'
   const prefix  = roleTag ? `[${roleTag}] ` : ''
   const end     = dayjs(r.start_at).add(r.total_time ?? 60, 'minute')
   return {
     title: `${prefix}${r.customer_name} / ${r.status}`,
     start: r.start_at,
     end:   end.toISOString(),
     extendedProps: { id: r.id, role: roleTag }
   }
 })
}
watch(selectedDate, loadEvents, { immediate:true })

/* ---------- クリック ---------- */
function handleEventClick(info){
  router.push(`${props.detailRoute}/${info.event.extendedProps.id}`)
}

/* ---------- ビュー切替 / 週送り ---------- */
function changeView(v){
  view.value = v
  calRef.value?.getApi().changeView(v, selectedDate.value.format('YYYY-MM-DD'))
}
function prevWeek(){ moveWeek(-7) }
function nextWeek(){ moveWeek( 7) }
function moveWeek(days){
  selectedDate.value = selectedDate.value.add(days,'day')
  weekDays.value = makeWeek()
  emit('date-change', selectedDate.value)     // 親にも通知
}

/* ---------- 日付クリック / Today ---------- */
function setDate(d){
  selectedDate.value = d
  calRef.value?.getApi().gotoDate(d.format('YYYY-MM-DD'))
  emit('date-change', d)
}
function goToday(){
  const t = dayjs()
  selectedDate.value = t
  weekDays.value     = makeWeek()
  calRef.value?.getApi().gotoDate(t.format('YYYY-MM-DD'))
  emit('date-change', t)
}
</script>

<template>
  <div class="timeline d-flex flex-column flex-grow-1">
    <!-- ▼ mini nav & 週ナビ -->
    <div class="mb-2 d-flex align-items-center gap-2 justify-content-end">
      <button class="btn btn-sm me-1"
        :class="view==='timeGridDay' ? 'btn-primary' : 'btn-outline-primary'"
        @click="changeView('timeGridDay')">Day</button>

      <button class="btn btn-sm me-3"
        :class="view==='timeGridWeek' ? 'btn-primary' : 'btn-outline-primary'"
        @click="changeView('timeGridWeek')">Week</button>

      <button class="btn btn-sm btn-outline-secondary" @click="prevWeek">‹</button>
      <button class="btn btn-sm btn-outline-primary"  @click="goToday">Today</button>
      <button class="btn btn-sm btn-outline-secondary" @click="nextWeek">›</button>
    </div>

    <!-- ▼ カスタム週ヘッダー -->
    <div class="timeline-header mb-2">
      <div class="wrap">
        <div v-for="d in weekDays" :key="d.format('YYYY-MM-DD')" class="weekday"
             @click="setDate(d)">
          <div class="weekday__wrap" :class="{ active:d.isSame(selectedDate,'day') }">
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
