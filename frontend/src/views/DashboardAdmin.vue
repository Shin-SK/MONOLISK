<script setup>
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import BillModal  from '@/components/BillModal.vue'
import BillListTable  from '@/components/BillListTable.vue'
import { api, fetchBill } from '@/api'
import { buildBillDraft } from '@/utils/draftbills.js'

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

function handleNewBill({ tableId }){
  currentBill.value = buildBillDraft({ tableId, storeId: myStoreId.value })
  showModal.value   = true
}

const tableRef = ref(null)  // ← 一覧の再読込用

function handleSaved(){
  showModal.value = false
  tableRef.value?.reload?.()  // ← BillListTable 側に reload() がある前提
}

/* ───────── 日付操作（必要ならこのまま） ───────── */
const selectedDate = ref(dayjs())
const selectedDateStr = computed({
  get:()=>selectedDate.value.format('YYYY-MM-DD'),
  set:v=>{ if(v) selectedDate.value = dayjs(v) }
})
const headerLabel = computed(()=>selectedDate.value.format('M月D日(ddd)'))
const isSame = d => selectedDate.value.isSame(d,'day')
function go(d){ selectedDate.value = selectedDate.value.add(d,'day') }
function setToday(){ selectedDate.value = dayjs() }
</script>

<template>
  <div class="dashboard">
    <div class="tables">
      <BillListTable
        ref="tableRef"
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
  </div>
</template>
