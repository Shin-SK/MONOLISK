<!-- views/DashboardAdmin.vue -->
<script setup>
import { ref, computed, nextTick, onMounted, reactive } from 'vue'
import dayjs from 'dayjs'
import GanttChart           from '@/components/GanttChart.vue'
import ReservationFormAdmin from '@/views/ReservationFormAdmin.vue'
import { Modal }   from 'bootstrap'
import { closeSidebarThen } from '@/utils/offcanvas'
import { yen } from '@/utils/money'
import { api }  from '@/api'
import AlertBell from '@/components/AlertBell.vue'


const selectedId = ref(null)
const modal      = ref(null)
const ganttRef   = ref(null)      // ⭐ 追加



const cashAlerts = ref([])        // 全アラート履歴


/* ───────── ガント表示日 ───────── */
const selectedDate = ref(dayjs())                 // ← 任意に変わる
const selectedDateStr = computed({
  get: () => selectedDate.value.format('YYYY-MM-DD'),
  set: v  => { if (v) selectedDate.value = dayjs(v) }
})
const isSame = d => selectedDate.value.isSame(d,'day')
function go(delta){ selectedDate.value = selectedDate.value.add(delta,'day') }
function setToday(){ selectedDate.value = dayjs() }

/* ───────── ヘッダー用 “リアル今日” ───────── */
const todayLabel = dayjs().format('YYYY.MM.DD (ddd)')

/* ───────── クリック予約 ───────── */
const formData   = reactive({ start_at: '', cast_id: null })

function handleRequestNew ({ castId, startISO }) {
  selectedId.value = null          // ref をここで触る
  nextTick(() => {
    formData.start_at = startISO
    formData.cast_id  = castId
    openModal()
  })
}

/* --- LocalStorage 永続化用キー (日付別) --- */
const STORAGE_KEY = `dismissedCash_${dayjs().format('YYYYMMDD')}`

const dismissed  = ref(new Set())        // 既読 driver_id Set

const visibleAlerts = computed(
  () => cashAlerts.value.filter(a => !dismissed.value.has(a.driver_id))
)
/* 初期ロード */
function loadDismissed () {
  try {
    dismissed.value = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'))
  } catch { /* 破損時は無視 */ }
}

/* 保存 */
function saveDismissed () {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...dismissed.value]))
}


/* ───────── モーダル  ───────── */
async function openModal () {
   closeSidebarThen(() => {
     modal.value = Modal.getOrCreateInstance('#reservationModal') // ★ ここで保持
     modal.value.show()
   })
}

async function openNew () {
  selectedId.value = null
  await nextTick()
  openModal()
}

async function handleBarClick ({ reservationId }) {
  selectedId.value = reservationId
  await nextTick()
  openModal()
}

function handleHide () {
  selectedId.value = null
}

async function handleSaved () {
  modal.value?.hide()
  await ganttRef.value?.reload?.()
}

onMounted(async () => {
  loadDismissed()
  const { data } = await api.get('/alerts/driver-cash/')
  // 時刻を埋め込みつつ履歴化
  cashAlerts.value = data.alerts.map(a => ({
    ...a,
    time: dayjs().format('HH:mm')
  }))
 })

function dismiss (id) {            // × ボタン用
  dismissed.value = new Set([...dismissed.value, id])
  saveDismissed()
}

</script>

<template>
  <!-- <h1 class="h2 text-center mb-5">ダッシュボード</h1> -->
  <div class="dashboard-admin container-fluid">
    <!-- ★ アラート -->
    <div v-if="visibleAlerts.length" class="mb-5">
      <div class="alert alert-danger alert-dismissible"
           v-for="a in visibleAlerts" :key="a.driver_id">
         {{ a.driver_name }} さんの所持金が
         <b>{{ yen(a.cash) }}</b> 円を超えています
        <button type="button" class="btn-close" @click="dismiss(a.driver_id)"></button>
      </div>
    </div>
    <!-- ─── 日付ヘッダー ─── -->
    <header class="gc-header d-flex align-items-center justify-content-between gap-3 mb-2">

      <div class="area d-flex align-center gap-4">
      <!-- ☆このボタン３つを変更したい -->
        <!-- ☆ひとつめのボタンは今日を基準に１クリックずつ前日へ -->
        <button
          class="btn btn-outline-secondary btn-nowrap"
          :class="{ active: selectedDate.isSame(dayjs().subtract(1, 'day'), 'day') }"
          @click="go(-1)"
        >
          <i class="bi bi-arrow-left"></i>
        </button>
       
        <button
          class="btn btn-outline-primary btn-nowrap"
          :class="{ active: isSame(dayjs()) }"
          @click="setToday"
        >今日</button>

        <!-- ☆みっつめのボタンは今日を基準に１クリックずつ明日へ -->
        <button
          class="btn btn-outline-secondary btn-nowrap"
          :class="{ active: selectedDate.isSame(dayjs().add(1, 'day'), 'day') }"
          @click="go(1)"
        >
          <i class="bi bi-arrow-right"></i>
        </button>

        <input type="date"
              class="form-control form-control-sm ms-2 bg-white"
              v-model="selectedDateStr"/>
      </div>

      <div class="area">
        <button class="btn btn-success btn-nowrap" @click="openNew">
          ＋ 新規予約
        </button>
      </div>

    </header>
    <div class="gantchart">
      <GanttChart
        ref="ganttRef" 
        :date="selectedDateStr"
        @bar-click="handleBarClick"
        :start-hour="10"
        :hours-per-chart="24"
        @request-new="handleRequestNew"
      />
    </div>
  </div>

  <!-- ─── Bootstrap5 モーダル ─── -->
  <div id="reservationModal"
       class="modal fade"
       tabindex="-1"
       @hidden.bs.modal="handleHide">
    <div class="modal-dialog modal-fullscreen p-4">
      <div class="modal-content">
        <div class="modal-header">
          <button class="btn-close" data-bs-dismiss="modal"></button>
        </div>

        <div class="modal-body p-0">
          <ReservationFormAdmin
              :key="selectedId ?? `${formData.start_at}_${formData.cast_id}`" 
              :reservationId="selectedId"
              :initial-data="formData"
              :in-modal="true"
              @saved="handleSaved"/>
        </div>
      </div>
    </div>
  </div>
</template>
