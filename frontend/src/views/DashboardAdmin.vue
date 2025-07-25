<script setup>
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'

import GanttChart from '@/components/GanttChart.vue'
import BillModal  from '@/components/BillModal.vue'

import { api, createBill, fetchBill } from '@/api'

/* ───────── 自店舗 ID ───────── */
const myStoreId = ref(null)
onMounted(async ()=>{
  try{
    const { data } = await api.get('billing/stores/me/')
    myStoreId.value = data.id
  }catch{/* 全店 */ }
})

/* ───────── Bill モーダル ───────── */
const showModal   = ref(false)
const currentBill = ref(null)

async function openBillEditor({ billId }){
  currentBill.value = await fetchBill(billId)
  showModal.value   = true
}

async function handleNewBill({ tableId }){
  const bill = await createBill(tableId)
  currentBill.value = bill
  showModal.value   = true
}

function handleSaved(){
  showModal.value = false
  ganttRef.value?.reload?.()
}

/* ───────── 日付操作 ───────── */
const selectedDate = ref(dayjs())
const selectedDateStr = computed({
  get:()=>selectedDate.value.format('YYYY-MM-DD'),
  set:v=>{ if(v) selectedDate.value = dayjs(v) }
})
const headerLabel = computed(()=>selectedDate.value.format('M月D日(ddd)'))
const isSame = d => selectedDate.value.isSame(d,'day')
function go(d){ selectedDate.value = selectedDate.value.add(d,'day') }
function setToday(){ selectedDate.value = dayjs() }


/* ───────── Gantt ref ───────── */
const ganttRef = ref(null)
</script>

<template>
<div class="dashboard-admin container-fluid">


  <!-- ▼ 日付ヘッダー -->
  <header class="gc-header position-relative mb-1">
    <div class="d-flex align-items-center justify-content-between gap-3 w-100">
      <div class="d-flex gap-3">
        <button class="btn btn-outline-secondary" :class="{active:isSame(dayjs().subtract(1,'day'))}" @click="go(-1)">
          <i class="bi bi-arrow-left"/>
        </button>
        <button class="btn btn-outline-primary" :class="{active:isSame(dayjs())}" @click="setToday">今日</button>
        <button class="btn btn-outline-secondary" :class="{active:isSame(dayjs().add(1,'day'))}" @click="go(1)">
          <i class="bi bi-arrow-right"/>
        </button>
        <input type="date" class="form-control form-control-sm bg-white ms-2" v-model="selectedDateStr"/>
      </div>

      <div class="position-absolute top-50 start-50 translate-middle fs-5 fw-bold">
        {{ headerLabel }}
      </div>

      <div>
        <button class="btn btn-success" @click="handleNewBill({ tableId:1 })">＋ 新規伝票</button>
      </div>
    </div>
  </header>
  <div class="d-flex gap-1 mt-5 mb-2">
      <div class="item badge text-white bg-danger">本指名</div>
      <div class="item badge text-white bg-success">場内</div>
      <div class="item badge text-white bg-blue">フリー(~10分)</div>
      <div class="item badge text-white bg-warning">フリー(~20分)</div>
      <div class="item badge text-white bg-orange">フリー(~30分)</div>
  </div>

  <!-- ▼ Gantt Chart -->
  <GanttChart
    ref="ganttRef"
    :date="selectedDateStr"
    :store-id="myStoreId"
    :start-hour="10"
    :hours-per-chart="24"
    @bill-click="openBillEditor"
    @request-new="handleNewBill"
  />

</div>

<!-- ▼ Bill 編集モーダル -->
<BillModal
  v-model="showModal"
  :bill="currentBill"
  @saved="handleSaved"
/>
</template>
