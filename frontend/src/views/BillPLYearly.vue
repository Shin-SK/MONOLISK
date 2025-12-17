<!-- src/views/BillPLYearly.vue -->
<script setup>
import { ref, onMounted, watch } from 'vue'
import { getBillYearlyPL, getBillYearlyPLForStore } from '@/api'

const props = defineProps({
  storeIds: { type: Array, default: () => [] }
})

/* -------- state -------- */
const year     = ref(new Date().getFullYear())
const pl       = ref(null)
const months   = ref([])
const loading  = ref(false)
const yen      = n => `¥${(+n || 0).toLocaleString()}`

/* -------- ダミー埋め -------- */
const blankTotals = {
  guest_count: 0, sales_total: 0, avg_spend: 0,
  labor_cost : 0, operating_profit: 0,
  sales_cash : 0, sales_card: 0,
  cast_labor : 0, driver_labor: 0,
  custom_expense: 0, gross_profit: 0
}

/* -------- fetch -------- */
async function fetchData(){
  loading.value = true
  const ids = (props.storeIds && props.storeIds.length) ? props.storeIds : []
  const storeId = localStorage.getItem('store_id')
  const finalIds = ids.length ? ids : (storeId ? [Number(storeId)] : [])

  try {
    if (finalIds.length > 1) {
      // 複数店舗：並列取得→合算
      const list = await Promise.all(
        finalIds.map(sid => getBillYearlyPLForStore(year.value, sid, { cache:false }).catch(()=>({ totals:{}, months:[] })))
      )
      
      // 月別を月でマージ
      const monthMap = new Map()
      for (const pl of list) {
        for (const m of (pl.months || [])) {
          if (!monthMap.has(m.month)) {
            monthMap.set(m.month, { month: m.month, totals: { ...blankTotals } })
          }
          const agg = monthMap.get(m.month).totals
          const src = m.totals || {}
          agg.sales_cash       += (Number(src.sales_cash) || 0)
          agg.sales_card       += (Number(src.sales_card) || 0)
          agg.sales_total      += (Number(src.sales_total) || 0)
          agg.guest_count      += (Number(src.guest_count) || 0)
          agg.labor_cost       += (Number(src.labor_cost) || 0)
          agg.operating_profit += (Number(src.operating_profit) || 0)
        }
      }
      months.value = Array.from(monthMap.values()).sort((a,b) => String(a.month).localeCompare(String(b.month)))
      
      // 年間totals合算
      const sum = (key) => list.reduce((a,b)=> a + (Number(b.totals?.[key])||0), 0)
      const totalGuests = sum('guest_count')
      const totalSales = sum('sales_total')
      pl.value = {
        year: year.value,
        totals: {
          sales_cash       : sum('sales_cash'),
          sales_card       : sum('sales_card'),
          sales_total      : totalSales,
          guest_count      : totalGuests,
          avg_spend        : totalGuests ? totalSales / totalGuests : 0,
          labor_cost       : sum('labor_cost'),
          operating_profit : sum('operating_profit'),
        }
      }
      // 月別の平均客単価も計算
      months.value.forEach(m => {
        const gc = m.totals.guest_count
        m.totals.avg_spend = gc ? m.totals.sales_total / gc : 0
      })
    } else {
      // 単店舗（既存）
      pl.value = await getBillYearlyPL(year.value)
      months.value = (pl.value.months ?? []).map(m => ({
        month : m.month,
        totals: { ...blankTotals, ...(m.totals ?? {}) }
      }))
      pl.value.totals = { ...blankTotals, ...(pl.value.totals ?? {}) }
    }
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
watch(() => props.storeIds, fetchData, { deep: true })
</script>

<template>
  <div class="pl pl-yearly py-2">
    <!-- フィルタ -->
    <div class="row g-3 align-items-center mb-3">
      <div class="col-8">
        <input id="yearInput" v-model="year" type="number" class="form-control bg-white w-100" min="2000" max="2100">
      </div>
      <div class="col-4">
        <button style="white-space: nowrap;"
          class="btn btn-sm btn-primary h-100 w-100" @click="fetchData">表示する</button>
      </div>
    </div>

    <div v-if="loading">読み込み中…</div>

    <template v-else-if="pl">
      <!-- YEAR SUMMARY -->
      <div class="summary-area row g-3 mb-3">
        <div class="col-12 col-md-4">
          <div class="box"><div class="head">年間売上</div><div class="number">{{ yen(pl.totals.sales_total) }}</div></div>
        </div>
        <div class="col-12 col-md-4">
          <div class="box"><div class="head">総来客数</div><div class="number">{{ pl.totals.guest_count }}</div></div>
        </div>
        <div class="col-12 col-md-4">
          <div class="box"><div class="head">平均客単価</div><div class="number">{{ yen(pl.totals.avg_spend) }}</div></div>
        </div>
        <div class="col-12 col-md-4">
          <div class="box"><div class="head">人件費</div><div class="number">{{ yen(pl.totals.labor_cost) }}</div></div>
        </div>
        <div class="col-12 col-md-4">
          <div class="box"><div class="head">営業利益</div><div class="number">{{ yen(pl.totals.operating_profit) }}</div></div>
        </div>
      </div>

      <!-- MONTH LIST -->
      <div class="table-responsive">
        <table class="table">
          <thead class="table-dark">
            <tr>
              <th>月</th>
              <th class="text-end">売上（現金/カード）</th>
              <th class="text-end">客数</th>
              <th class="text-end">平均客単価</th>
              <th class="text-end">人件費</th>
              <th class="text-end">営業利益</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in months" :key="m.month">
              <td>{{ m.month }}</td>
              <td class="text-end">
                <span class="fw-bold">{{ yen(m.totals.sales_total) }}</span>
                ({{ yen(m.totals.sales_cash) }}/{{ yen(m.totals.sales_card) }})</td>
              <td class="text-end">{{ m.totals.guest_count }}</td>
              <td class="text-end">{{ yen(m.totals.avg_spend) }}</td>
              <td class="text-end">{{ yen(m.totals.labor_cost) }}</td>
              <td class="text-end" :class="{ 'fw-semibold': true, 'text-danger': m.totals.operating_profit < 0 }">
                {{ yen(m.totals.operating_profit) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.pl-yearly input { min-width:130px }

.table > :not(caption) > * > * {
  padding: 1.5rem;
}

td,th{
  text-wrap: nowrap;
}

</style>
