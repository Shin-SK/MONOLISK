<!-- frontend/src/views/DashboardAdmin.vue -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import dayjs from 'dayjs'
import BillModal       from '@/components/BillModal.vue'
import BillListTable   from '@/components/BillListTable.vue'   // PC用（現行DnD）
import BillTablesSP    from '@/components/BillTablesSP.vue'    // ← 新規（上で作成）
import { api, fetchBill } from '@/api'
import { buildBillDraft } from '@/utils/draftbills.js'
import { startTxQueue } from '@/utils/txQueue'
startTxQueue()

/* ── SP/PC 判定 ── */
const isSP = ref(false)
function updateIsSP(){ isSP.value = matchMedia('(max-width: 768px)').matches }
onMounted(() => {
  updateIsSP()
  window.addEventListener('resize', updateIsSP)
})
onBeforeUnmount(()=> window.removeEventListener('resize', updateIsSP))

/* ───────── 店舗 ID ───────── */
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

const pcRef = ref(null)
const spRef = ref(null)

function handleSaved(){
  showModal.value = false
  pcRef.value?.reload?.()
  spRef.value?.reload?.()
}

/* （日付UIは既存のまま必要なら） */
</script>

<template>
  <div class="dashboard">
    <div class="tables">
      <component
        :is="isSP ? BillTablesSP : BillListTable"
        :ref="isSP ? 'spRef' : 'pcRef'"
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
