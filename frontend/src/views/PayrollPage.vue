<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { fetchPayrollSummary } from '@/api'

const router   = useRouter()
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))
const rows     = ref([])
const loading  = ref(false)
const errorMsg = ref('')

const yen = n => `¥${(Number(n||0)).toLocaleString()}`
const h   = m => (Math.round(((m||0)/60)*100)/100).toFixed(2) // 分→時間(小数2)

async function load(){
  loading.value = true
  errorMsg.value = ''
  try{
    rows.value = await fetchPayrollSummary({ from: dateFrom.value, to: dateTo.value })
  }catch(e){
    console.error(e); errorMsg.value = '取得に失敗しました'
  }finally{
    loading.value = false
  }
}
function openDetail(r){
  router.push({ name:'PayrollCastDetail', params:{ id:r.id }, query:{ from:dateFrom.value, to:dateTo.value } })
}
onMounted(load)
</script>

<template>
  <div class="container-fluid py-3">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h1 class="h5 mb-0">給与</h1>
      <div class="d-flex gap-2">
        <input v-model="dateFrom" type="date" class="form-control form-control-sm" />
        <input v-model="dateTo"   type="date" class="form-control form-control-sm" />
        <button class="btn btn-primary btn-sm" @click="load">再読込</button>
      </div>
    </div>

    <div v-if="errorMsg" class="alert alert-danger">{{ errorMsg }}</div>
    <div v-if="loading">Loading…</div>

    <div v-if="!loading && rows.length===0" class="text-muted">データがありません</div>

    <div v-if="rows.length" class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th>キャスト</th>
            <th class="text-end">総勤務時間(h)</th>
            <th class="text-end">時給合計</th>
            <th class="text-end">歩合</th>
            <th class="text-end">総額</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id" @click="openDetail(r)" style="cursor:pointer">
            <td>{{ r.stage_name }}</td>
            <td class="text-end">{{ h(r.worked_min) }}</td>
            <td class="text-end">{{ yen(r.hourly_pay) }}</td>
            <td class="text-end">{{ yen(r.commission) }}</td>
            <td class="text-end fw-bold">{{ yen(r.total) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
