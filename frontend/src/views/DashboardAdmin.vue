<!-- frontend/src/views/DashboardAdmin.vue -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import BillModal       from '@/components/BillModal.vue'
import BillBoardPC     from '@/components/BillBoardPC.vue'     // PC用（伝票中心）
import BillBoardSP     from '@/components/BillBoardSP.vue'     // SP用（伝票中心）
import { api, fetchBill } from '@/api'
import { useBills } from '@/stores/useBills'
import { buildBillDraft } from '@/utils/draftbills.js'
import { startTxQueue } from '@/utils/txQueue'
startTxQueue()

const route = useRoute()
const router = useRouter()

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

function handleNewBill({ tableId, tableIds }){
  const ids = tableIds || (tableId ? [tableId] : [])
  const d = buildBillDraft({ tableIds: ids, storeId: myStoreId.value }) || {}
  if (ids.length === 1) {
    d.table = d.table || { id: ids[0] }
    d.table_id_hint = ids[0]
  }
  currentBill.value = d
  showModal.value   = true
}

// 注意: ref() ではなく素のオブジェクト。template 内で auto-unwrap されると
// `spRef.value = el` が `null.value = el` になりエラーになるため。
const boardRef = { pc: null, sp: null }
const billsStore = useBills()

// SP/PC ref が動的バインド（:ref="isSP ? spRef : pcRef"）でうまく解決されない
// ケースに備え、保存後は必ず billsStore を直接 reload する。
async function handleSaved(){
  showModal.value = false
  try {
    await billsStore.loadAll(true)
  } catch (e) { console.error('[DashboardAdmin] reload after save failed', e) }
  boardRef.pc?.reload?.()
  boardRef.sp?.reload?.()
}

async function tryOpenBillFromRoute(){
  const billId = route.query.billId
  if(!billId) return

  await openBillEditor({ billId })

  const { billId: _removed, ...rest } = route.query
  router.replace({ query: rest })
}

watch(
  () => route.query.billId,
  () => { void tryOpenBillFromRoute() },
  { immediate: true }
)

</script>

<template>
  <div class="dashboard">
    <div class="tables">
      <component
        :is="isSP ? BillBoardSP : BillBoardPC"
        :ref="el => { if (isSP) boardRef.sp = el; else boardRef.pc = el }"
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
