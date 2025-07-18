<script setup>
import { ref, onMounted } from 'vue'
import { getBillMonthlyPL, getStores } from '@/api'

const monthStr = ref(new Date().toISOString().slice(0,7))   // 'YYYY-MM'
const storeId  = ref('')
const stores   = ref([])
const pl       = ref(null)

const yen = n => `¥${(+n||0).toLocaleString()}`

async function fetchData () {
  pl.value = await getBillMonthlyPL(monthStr.value, storeId.value)
}

onMounted(async () => {
  stores.value = await getStores()
  await fetchData()
})
</script>

<template>
  <div class="pl-monthly p-4">
    <h3 class="mb-3">月次 P/L</h3>

    <div class="d-flex gap-2 mb-3">
      <input type="month" v-model="monthStr" class="form-control w-auto" />
      <select v-model="storeId" class="form-select w-auto">
        <option value="">全店舗</option>
        <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <button class="btn btn-primary" @click="fetchData">読み込み</button>
    </div>

    <!-- 月次サマリ -->
    <table v-if="pl" class="table table-bordered table-striped mb-4">
      <tbody>
        <tr><th class="w-50">対象月</th><td>{{ pl.year }}‑{{ pl.month }}</td></tr>
        <tr><th>店舗</th><td>{{ pl.store_id || '全店舗' }}</td></tr>
        <tr><th>来客数</th><td>{{ pl.totals.guest_count }}</td></tr>
        <tr><th>売上合計</th><td>{{ yen(pl.totals.sales_total) }}</td></tr>
        <tr><th>平均客単価</th><td>{{ yen(pl.totals.avg_spend) }}</td></tr>
        <tr><th>ドリンク売上</th><td>{{ yen(pl.totals.drink_sales) }}</td></tr>
        <tr><th>ドリンク杯数</th><td>{{ pl.totals.drink_qty }}</td></tr>
        <tr><th>ドリンク単価</th><td>{{ yen(pl.totals.drink_unit_price) }}</td></tr>
        <tr><th>延長回数</th><td>{{ pl.totals.extension_qty }}</td></tr>
      </tbody>
    </table>

    <!-- 日次一覧 -->
    <table v-if="pl" class="table table-sm table-bordered">
      <thead class="table-light">
        <tr>
          <th>日付</th><th>客数</th><th>売上</th><th>平均客単価</th>
          <th>ドリンク売上</th><th>杯数</th><th>延長</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in pl.days" :key="d.date">
          <td>{{ d.date }}</td>
          <td>{{ d.guest_count }}</td>
          <td>{{ yen(d.sales_total) }}</td>
          <td>{{ yen(d.avg_spend) }}</td>
          <td>{{ yen(d.drink_sales) }}</td>
          <td>{{ d.drink_qty }}</td>
          <td>{{ d.extension_qty }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else>読み込み中…</div>
  </div>
</template>

<style scoped>
.pl-monthly input,
.pl-monthly select { min-width: 130px; }
</style>
