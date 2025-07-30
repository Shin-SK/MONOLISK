<!-- src/views/BillPLYearly.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { getBillYearlyPL, getStores } from '@/api'

const year     = ref(new Date().getFullYear())
const storeId  = ref(1)
const stores   = ref([])
const pl       = ref(null)

const yen = n => `¥${(+n || 0).toLocaleString()}`

async function fetchData () {
  pl.value = null                         // いったん空 → “読み込み中” 表示
  pl.value = await getBillYearlyPL(year.value, storeId.value)
}

onMounted(async () => {
  stores.value = await getStores()
  await fetchData()
})
</script>

<template>
  <div class="pl pl-yearly">

    <!-- ▼ 年間サマリ & 月次一覧：pl が取得できてから描画 -->
    <div v-if="pl">
      <!-- ── YEAR SUMMARY ───────────────────────────── -->
      <div class="summary-area mb-3">
        <div class="box"><div class="head">年間売上</div><div class="number">{{ yen(pl.totals.sales_total) }}</div></div>
        <div class="box"><div class="head">総来客数</div><div class="number">{{ pl.totals.guest_count }}</div></div>
        <div class="box"><div class="head">平均客単価</div><div class="number">{{ yen(pl.totals.avg_spend) }}</div></div>
        <div class="box"><div class="head">ドリンク売上</div><div class="number">{{ yen(pl.totals.drink_sales) }}</div></div>
        <div class="box"><div class="head">延長回数</div><div class="number">{{ pl.totals.extension_qty }}</div></div>
        <div class="box"><div class="head">人件費</div><div class="number">{{ yen(pl.totals.labor_cost) }}</div></div>
        <div class="box"><div class="head">営業利益</div><div class="number">{{ yen(pl.totals.operating_profit) }}</div></div>
      </div>

      <!-- ── 月次一覧 ─────────────────────────────── -->
      <table class="table table-sm table-bordered">
        <thead class="table-light">
          <tr>
            <th>月</th><th>客数</th><th>売上</th><th>平均客単価</th>
            <th>ドリンク売上</th><th>杯数</th><th>延長</th>
            <th>人件費</th><th>営業利益</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in pl.months" :key="m.month">
            <td>{{ m.month }}</td>
            <td>{{ m.totals.guest_count }}</td>
            <td>{{ yen(m.totals.sales_total) }}</td>
            <td>{{ yen(m.totals.avg_spend) }}</td>
            <td>{{ yen(m.totals.drink_sales) }}</td>
            <td>{{ m.totals.drink_qty }}</td>
            <td>{{ m.totals.extension_qty }}</td>
            <td>{{ yen(m.totals.labor_cost) }}</td>
            <td>{{ yen(m.totals.operating_profit) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ▼ フィルタ UI（共通なので常時表示） -->
    <div class="d-flex gap-2 mb-3">
      <input type="number" v-model="year" class="form-control w-auto" min="2000" max="2100" />
      <select v-model="storeId" class="form-select w-auto">
        <option value="">全店舗</option>
        <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <button class="btn btn-primary" @click="fetchData">読み込み</button>
    </div>

    <!-- 読み込み中 -->
    <div v-if="pl === null">読み込み中…</div>
  </div>
</template>

<style scoped>
.pl-yearly input,
.pl-yearly select { min-width: 130px; }
</style>
