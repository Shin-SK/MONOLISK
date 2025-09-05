<script setup>
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import { useRoute } from 'vue-router'
import { api, fetchBills, fetchBill } from '@/api'
import BillModalSP from '@/components/BillModalSP.vue'   // ← 本家モーダル

const route = useRoute()

const list    = ref([])
const loading = ref(false)
const show    = ref(false)
const bill    = ref(null)  // BillModalSP に渡すオブジェクト

async function load(){
  loading.value = true
  try{
    const data = await fetchBills({ limit: 100 })
    list.value = (Array.isArray(data.results) ? data.results : data).sort((a,b)=> dayjs(b.opened_at) - dayjs(a.opened_at))
  }finally{ loading.value = false }
}

async function openBill(id){
  const b = await fetchBill(id).catch(()=>null)
  if (!b){ alert('伝票を取得できませんでした'); return }
  bill.value = b
  show.value = true
}

async function newBill(){
  // 必要なら table_id を選ばせるUIに差し替え
  const { data: created } = await api.post('billing/bills/', {
    table_id: null, opened_at: new Date().toISOString(), expected_out: null,
  })
  await openBill(created.id)
  await load()
}

function onSaved(){ load() }
function onUpdated(){ load() }
function onClosed(){ show.value = false; load() }

onMounted(async () => {
  await load()
  const q = Number(route.query?.bill || 0) || null
  if (q) openBill(q)
})
</script>

<template>
  <div class="container">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="m-0">伝票一覧</h5>
      <button class="btn btn-primary" @click="newBill">新規伝票</button>
    </div>

    <div v-if="loading" class="text-muted">読み込み中…</div>
    <div v-else class="list-group">
      <button v-for="b in list" :key="b.id" class="list-group-item d-flex justify-content-between align-items-center"
              @click="openBill(b.id)">
        <span>#{{ b.id }} / 卓{{ b.table?.number ?? '-' }} / {{ dayjs(b.opened_at).format('MM/DD HH:mm') }}</span>
        <small class="text-muted">{{ b.closed_at ? 'CLOSED' : 'OPEN' }}</small>
      </button>
      <div v-if="!list.length" class="text-muted">伝票がありません。</div>
    </div>

    <!-- 本家モーダル -->
    <BillModalSP
      v-if="bill"
      v-model="show"
      :bill="bill"
      @saved="onSaved"
      @updated="onUpdated"
      @closed="onClosed"
    />
  </div>
</template>
