<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { fetchPayrollDetail, downloadPayrollDetailCsv } from '@/api'

const route = useRoute()
const router = useRouter()
const castId = Number(route.params.id)
const dateFrom = ref(route.query.from || dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(route.query.to   || dayjs().format('YYYY-MM-DD'))

const data = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const yen = n => `¥${(Number(n||0)).toLocaleString()}`
const hhmm = iso => iso ? dayjs(iso).format('YYYY/MM/DD HH:mm') : '—'

async function exportCsv() {
  try {
    const blob = await downloadPayrollDetailCsv(castId, { from: dateFrom.value, to: dateTo.value })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    const name = `payroll_${data.value?.cast?.stage_name || castId}_${dateFrom.value}_to_${dateTo.value}.csv`
    a.href = url
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    alert('CSVのダウンロードに失敗しました')
  }
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try{
    data.value = await fetchPayrollDetail(castId, { from: dateFrom.value, to: dateTo.value })
  }catch(e){
    console.error(e); errorMsg.value = '取得に失敗しました'
  }finally{
    loading.value = false
  }
}

const totals = computed(() => data.value?.totals || { total_hours:0, hourly_pay:0, commission:0, total:0 })
onMounted(load)
</script>

<template>
  <div class="container-fluid py-3">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h1 class="h5 mb-0">給与詳細 — {{ data?.cast?.stage_name || '' }}</h1>
      <div class="d-flex gap-2">
        <input v-model="dateFrom" type="date" class="form-control form-control-sm bg-white" />
        <input v-model="dateTo"   type="date" class="form-control form-control-sm bg-white" />
        <button class="btn btn-primary btn-sm" @click="load">再読込</button>
		<button class="btn btn-outline-secondary btn-sm" @click="exportCsv">CSVダウンロード</button>
        <button class="btn btn-outline-secondary btn-sm" @click="router.back()">戻る</button>
      </div>
    </div>

    <div v-if="errorMsg" class="alert alert-danger">{{ errorMsg }}</div>
    <div v-if="loading">Loading…</div>

    <div v-if="data">
      <div class="card mb-3">
        <div class="card-body d-flex flex-wrap gap-4">
          <div>総勤務時間: <b>{{ Number(totals.total_hours).toFixed(2) }} h</b></div>
          <div>時給合計: <b>{{ yen(totals.hourly_pay) }}</b></div>
          <div>歩合: <b>{{ yen(totals.commission) }}</b></div>
          <div>総額: <b>{{ yen(totals.total) }}</b></div>
        </div>
      </div>

      <h6 class="mt-3 fw-bold">勤務（時給）</h6>
      <div class="table-responsive mb-4">
        <table class="table table-sm align-middle">
          <thead>
            <tr>
              <th>出勤</th><th>退勤</th>
              <th class="text-end">分</th>
              <th class="text-end">時給</th>
              <th class="text-end">金額</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!data.shifts?.length">
              <td colspan="5" class="text-muted">シフトがありません</td>
            </tr>
            <tr v-for="s in data.shifts" :key="s.id">
              <td>{{ hhmm(s.clock_in) }}</td>
              <td>{{ hhmm(s.clock_out) }}</td>
              <td class="text-end">{{ s.worked_min ?? 0 }}</td>
              <td class="text-end">{{ yen(s.hourly_wage_snap) }}</td>
              <td class="text-end">{{ yen(s.payroll_amount) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h6 class="fw-bold">歩合（伝票明細）</h6>
      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead>
            <tr>
              <th>伝票</th>
              <th>明細</th>
              <th class="text-end">金額</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!data.payouts?.length">
              <td colspan="3" class="text-muted">歩合がありません</td>
            </tr>
            <tr v-for="p in data.payouts" :key="p.id">
              <td>
                <router-link :to="`/bills/${p.bill?.id || ''}`">
                  #{{ p.bill?.id || '-' }}
                </router-link>
              </td>
              <td>#{{ p.bill_item?.id || '-' }}</td>
              <td class="text-end">{{ yen(p.amount) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>


<style scoped>
	button{
		white-space: nowrap;
	}
</style>