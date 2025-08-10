<!-- src/views/DashboardGantt.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import GanttChart from '@/components/GanttChart.vue'
import BillModal  from '@/components/BillModal.vue'
import { buildBillDraft } from '@/utils/draftbills'
import { api, fetchBill } from '@/api'

/* ───────── 店舗 ID ───────── */
const myStoreId = ref(null)
onMounted(async () => {
  try {
    const { data } = await api.get('billing/stores/me/')
    myStoreId.value = data.id
  } catch { /* 全店モード */ }
})

/* ───────── Bill モーダル ───────── */
const showModal   = ref(false)
const currentBill = ref(null)

async function openBillEditor({ billId }) {
  const bill = await fetchBill(billId)
  currentBill.value = bill
  showModal.value   = true
}

function handleNewBill({ tableId }) {
  currentBill.value = buildBillDraft({ tableId, storeId: myStoreId.value })
  showModal.value   = true
}

function handleSaved() {
  showModal.value = false
  ganttRef.value?.reload?.()   // コンポーネント側に reload() がある想定
}

/* ───────── 日付操作 ───────── */
const selectedDate = ref(dayjs())
const selectedDateStr = computed({
  get: () => selectedDate.value.format('YYYY-MM-DD'),
  set: v  => { if (v) selectedDate.value = dayjs(v) }
})
const headerLabel = computed(() => selectedDate.value.format('M月D日(ddd)'))
const isSame  = d => selectedDate.value.isSame(d, 'day')
const go      = d => selectedDate.value = selectedDate.value.add(d, 'day')
const setToday = () => selectedDate.value = dayjs()

/* ───────── Gantt ref ───────── */
const ganttRef = ref(null)

</script>

<template>
  <div class="gantt dashboard container-fluid d-flex flex-column">
    <div class="outer flex-fill position-relative">
      <!-- ▼ 日付ヘッダー -->
      <header class="gc-header position-relative mb-1">
        <div class="d-flex align-items-center justify-content-between gap-3 w-100">
          <!-- 凡例 -->
          <div class="d-flex gap-1">
            <span class="badge bg-danger text-white">本指名</span>
            <span class="badge bg-success text-white">場内</span>
            <span class="badge bg-blue text-white">フリー(~10分)</span>
            <span class="badge bg-warning text-white">フリー(~20分)</span>
            <span class="badge bg-orange text-white">フリー(~30分)</span>
          </div>

          <div class="position-absolute top-50 start-50 translate-middle fs-5 fw-bold">
            {{ headerLabel }}
          </div>

          <div class="d-flex gap-3">
            <input
              v-model="selectedDateStr"
              type="date"
              class="form-control form-control-sm bg-white ms-2"
            >
            <button
              class="btn btn-outline-secondary"
              :class="{active:isSame(dayjs().subtract(1,'day'))}"
              @click="go(-1)"
            >
              <IconArrowLeft />
            </button>
            <button
              class="btn btn-outline-primary"
              :class="{active:isSame(dayjs())}"
              @click="setToday"
            >
              今日
            </button>
            <button
              class="btn btn-outline-secondary"
              :class="{active:isSame(dayjs().add(1,'day'))}"
              @click="go(1)"
            >
              <IconArrowRight />
            </button>
          </div>
        </div>
      </header>

      <!-- ▼ Gantt Chart 本体 -->
      <GanttChart
        v-if="myStoreId !== null"
        ref="ganttRef"
        :date="selectedDateStr"
        :store-id="myStoreId"
        :start-hour="10"
        :hours-per-chart="24"
        @bill-click="openBillEditor"
        @request-new="handleNewBill"
      />

      <div class="add-button position-fixed">
        <button
          class="btn btn-success rounded-circle"
          @click="handleNewBill({ tableId:1 })"
        >
          ＋
        </button>
      </div>
    </div><!-- /outer -->

    <!-- ▼ Bill 編集モーダル -->
    <BillModal
      v-model="showModal"
      :bill="currentBill"
      @saved="handleSaved"
    />
  </div><!-- /gantt-dashboard -->
</template>

<style scoped>
/* 必要に応じて調整 */
</style>
