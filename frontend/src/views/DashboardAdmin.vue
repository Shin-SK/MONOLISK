<script setup>
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import BillModal  from '@/components/BillModal.vue'
import BillListTable  from '@/components/BillListTable.vue'


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
  <div class="dashboard">
    <div class="tables">
      <BillListTable />
    </div>
    <!-- ▼ Bill 編集モーダル -->
    <BillModal
      v-model="showModal"
      :bill="currentBill"
      @saved="handleSaved"
    />

  </div>
</template>
