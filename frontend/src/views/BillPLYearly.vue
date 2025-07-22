<script setup>
import { ref, onMounted } from 'vue'
import { getBillYearlyPL, getStores } from '@/api'

const year     = ref(new Date().getFullYear())
const storeId  = ref('')
const stores   = ref([])
const pl       = ref(null)

const yen = n => `¥${(+n||0).toLocaleString()}`

async function fetchData () {
  pl.value = await getBillYearlyPL(year.value, storeId.value)
}

onMounted(async () => {
  stores.value = await getStores()
  await fetchData()
})
</script>

<template>
  <div class="pl pl-yearly">

    <div class="summary-area">
      <div class="box">
        <div class="head">年間売上</div>
        <div class="number">{{ yen(pl.totals.sales_total) }}</div>
      </div>

      <div class="box">
        <div class="head">総来客数</div>
        <div class="number">{{ pl.totals.guest_count }}</div>
      </div>
      <div class="box">
        <div class="head">平均客単価</div>
        <div class="number">{{ yen(pl.totals.avg_spend) }}</div>
      </div>

      <div class="box">
        <div class="head">ドリンク売上</div>
        <div class="number">{{ yen(pl.totals.drink_sales) }}</div>
      </div>
      <div class="box">
        <div class="head">延長回数</div>
        <div class="number">{{ pl.totals.extension_qty }}</div>
      </div>
    </div>

    <div class="d-flex gap-2 mb-3">
      <input type="number" v-model="year" class="form-control w-auto" min="2000" max="2100" />
      <select v-model="storeId" class="form-select w-auto">
        <option value="">全店舗</option>
        <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <button class="btn btn-primary" @click="fetchData">読み込み</button>
    </div>

    <!-- 年間サマリ -->
    <!-- <table v-if="pl" class="table table-bordered mb-4">
      <tbody>
        <tr><th class="w-50">対象年</th><td>{{ pl.year }}</td></tr>
        <tr><th>店舗</th><td>{{ pl.store_id || '全店舗' }}</td></tr>
        <tr><th>来客数</th><td>{{ pl.totals.guest_count }}</td></tr>
        <tr><th>売上合計</th><td>{{ yen(pl.totals.sales_total) }}</td></tr>
        <tr><th>平均客単価</th><td>{{ yen(pl.totals.avg_spend) }}</td></tr>
        <tr><th>ドリンク売上</th><td>{{ yen(pl.totals.drink_sales) }}</td></tr>
        <tr><th>ドリンク杯数</th><td>{{ pl.totals.drink_qty }}</td></tr>
        <tr><th>ドリンク単価</th><td>{{ yen(pl.totals.drink_unit_price) }}</td></tr>
        <tr><th>延長回数</th><td>{{ pl.totals.extension_qty }}</td></tr>
      </tbody>
    </table> -->

    <!-- 月次一覧 -->
    <table v-if="pl" class="table table-sm table-bordered">
      <thead class="table-light">
        <tr>
          <th>月</th><th>客数</th><th>売上</th><th>平均客単価</th>
          <th>ドリンク売上</th><th>杯数</th><th>延長</th>
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
        </tr>
      </tbody>
    </table>

    <div v-else>読み込み中…</div>
  </div>
</template>

<style scoped>
.pl-yearly input,
.pl-yearly select { min-width: 130px; }
</style>
