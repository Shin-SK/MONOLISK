<script setup>
import { ref, watchEffect } from 'vue'
import { getBillYearlyPL }  from '@/api'

/* -------- state -------- */
const year     = ref(new Date().getFullYear())
const pl       = ref(null)      // API 全体
const months   = ref([])        // 1-12 行
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
    <!-- ── フィルタ ────────────────────────── -->
    <div class="d-flex gap-2 mb-3">
      <input
        v-model="year"
        type="number"
        class="form-control w-auto"
        min="2000"
        max="2100"
      >
    </div>

    <!-- ── 読み込み中 ────────────────────── -->
    <div v-if="loading">
      読み込み中…
    </div>

    <!-- ── 本体 ─────────────────────────── -->
    <template v-else-if="pl">
      <!-- YEAR SUMMARY -->
      <div class="summary-area mb-3">
        <div class="box">
          <div class="head">
            年間売上
          </div>     <div class="number">
            {{ yen(pl.totals.sales_total) }}
          </div>
        </div>
        <div class="box">
          <div class="head">
            総来客数
          </div>     <div class="number">
            {{ pl.totals.guest_count }}
          </div>
        </div>
        <div class="box">
          <div class="head">
            平均客単価
          </div>   <div class="number">
            {{ yen(pl.totals.avg_spend) }}
          </div>
        </div>
        <div class="box">
          <div class="head">
            人件費
          </div>       <div class="number">
            {{ yen(pl.totals.labor_cost) }}
          </div>
        </div>
        <div class="box">
          <div class="head">
            営業利益
          </div>     <div class="number">
            {{ yen(pl.totals.operating_profit) }}
          </div>
        </div>
      </div>

      <!-- MONTH LIST -->
      <table class="table table-sm table-bordered">
        <thead class="table-light">
          <tr>
            <th>月</th><th>客数</th><th>売上</th><th>平均客単価</th>
            <th>人件費</th><th>営業利益</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="m in months"
            :key="m.month"
          >
            <td>{{ m.month }}</td>
            <td>{{ m.totals.guest_count }}</td>
            <td>{{ yen(m.totals.sales_total) }}</td>
            <td>{{ yen(m.totals.avg_spend) }}</td>
            <td>{{ yen(m.totals.labor_cost) }}</td>
            <td>{{ yen(m.totals.operating_profit) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<style scoped>
.summary-area { display:flex; flex-wrap:wrap; gap:1rem }
.summary-area .box { background:#f5f5f5; padding:1rem; border-radius:.5rem; min-width:120px; flex:1 }
.summary-area .head   { font-size:.8rem; color:#555 }
.summary-area .number { font-size:1.1rem; font-weight:700 }
.pl-yearly input { min-width:130px }
</style>
