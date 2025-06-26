<!-- views/DashboardAdmin.vue -->
<script setup>
import { ref, computed, nextTick } from 'vue'
import dayjs from 'dayjs'
import GanttChart           from '@/components/GanttChart.vue'
import ReservationFormAdmin from '@/views/ReservationFormAdmin.vue'

const selectedId = ref(null)
const modal      = ref(null)

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


/* ───────── モーダル  ───────── */
async function openModal () {
  if (!modal.value) {
    const { Modal } = await import('bootstrap')
    modal.value = new Modal(document.getElementById('reservationModal'))
  }
  modal.value.show()
}

async function openNew () {
  selectedId.value = null         // ← id を消して「新規」扱い
  await nextTick()                // コンポーネントを差し替えてから
  openModal()                     // モーダルを表示
}


/* ★ async を付け、selectedId をセットしてから nextTick → show() */
async function handleBarClick ({ reservationId }) {
  selectedId.value = reservationId          // ① 値が入る
  await nextTick()                           // ② DOM が updated

  if (!modal.value) {                        // ③ 初回だけ import
    const { Modal } = await import('bootstrap')
    modal.value = new Modal(document.getElementById('reservationModal'))
  }
  modal.value.show()                         // ④ 表示
}

function handleHide () {
  selectedId.value = null
}

/* script setup 内に追加 */
function handleSaved () {
  modal.value?.hide()
}
</script>

<template>
  <h1 class="h2 text-center mb-5">ダッシュボード</h1>
  <div class="dashboard-admin container-md">
    
    <!-- ─── 日付ヘッダー ─── -->
    <header class="gc-header d-flex align-items-center justify-content-between gap-3 mb-2">
      <!-- ← ここは常に “今日” -->
      <h5 class="mb-0">{{ todayLabel }}</h5>

      <button class="btn btn-success btn-nowrap" @click="openNew">
        ＋ 新規予約
      </button>

      <div class="wrap d-flex align-center gap-4">
      <!-- コントロール -->
        <button
          class="btn btn-outline-secondary btn-nowrap"
          :class="{ active: isSame(selectedDate.subtract(1,'day')) }"
          @click="go(-1)"
        >昨日</button>

        <button
          class="btn btn-outline-primary btn-nowrap"
          :class="{ active: isSame(dayjs()) }"
          @click="setToday"
        >今日</button>

        <button
          class="btn btn-outline-secondary btn-nowrap"
          :class="{ active: isSame(selectedDate.add(1,'day')) }"
          @click="go(1)"
        >明日</button>

        <input type="date"
              class="form-control form-control-sm ms-2"
              v-model="selectedDateStr"/>
      </div>

    </header>
    <div class="gantchart">
      <GanttChart
        :date="selectedDateStr"
        @bar-click="handleBarClick"
          :start-hour="10"
          :hours-per-chart="24"
      />
    </div>
  </div>

  <!-- ─── Bootstrap5 モーダル ─── -->
  <div id="reservationModal"
       class="modal fade"
       tabindex="-1"
       @hidden.bs.modal="handleHide">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">予約詳細</h5>
          <button class="btn-close" data-bs-dismiss="modal"></button>
        </div>

        <div class="modal-body p-0">
          <ReservationFormAdmin
              :key="selectedId ?? 'new'"
              :reservationId="selectedId"
              :in-modal="true"
              @saved="handleSaved" />
        </div>
      </div>
    </div>
  </div>
</template>
