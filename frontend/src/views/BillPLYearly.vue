<!-- src/views/BillPLYearly.vue -->
<script setup>
import { ref, watchEffect } from 'vue'
import { getBillYearlyPL }  from '@/api'

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
watchEffect(async () => {
  loading.value = true
  try {
    pl.value = await getBillYearlyPL(year.value)

    /* months (必ず 12 行) */
    months.value = (pl.value.months ?? []).map(m => ({
      month : m.month,
      totals: { ...blankTotals, ...(m.totals ?? {}) }
    }))

    /* 年間 totals も欠損補完 */
    pl.value.totals = { ...blankTotals, ...(pl.value.totals ?? {}) }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="pl pl-yearly container-fluid py-4">
    <!-- フィルタ -->
    <div class="d-flex gap-2 mb-3">
      <input v-model="year" type="number" class="form-control w-auto" min="2000" max="2100">
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
