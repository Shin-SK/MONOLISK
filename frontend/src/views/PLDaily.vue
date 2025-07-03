<!-- src/components/PLDaily.vue -->
<script setup>
import { ref, onMounted, watch } from 'vue'
import { getStores, getDailyPL } from '@/api'   // ← ラッパー関数
import dayjs from 'dayjs'
import { yen } from '@/utils/money'

/* ---- 画面状態 ------------------------------------------------ */
const today   = dayjs().format('YYYY-MM-DD')
const date    = ref(today)
const store   = ref('')           // '' = 全店舗
const stores  = ref([])
const row     = ref(null)         // API 1 レコード

/* ---- マスタ取得 --------------------------------------------- */
async function fetchStores () {
  stores.value = await getStores()
}

/* ---- 日次 P/L 取得 ------------------------------------------- */
async function fetchPL () {
  row.value = await getDailyPL(date.value, store.value)
}

/* ---- 初期化 & 自動再読込 ------------------------------------ */
onMounted(async () => {
  await fetchStores()
  await fetchPL()
})
watch([date, store], fetchPL)
</script>

<template>
  <div class="container py-4">
    <h1 class="h4 mb-3">デイリー P/L</h1>

    <!-- フィルタ -->
    <div class="d-flex gap-3 mb-4">
      <input type="date" v-model="date" class="form-control" style="max-width:180px">
      <select v-model="store" class="form-select" style="max-width:200px">
        <option value="">全店舗</option>
        <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>

    <!-- 表 -->
    <table v-if="row" class="table table-bordered w-100">
      <thead class="table-dark text-center">
        <tr>
          <th width="130">項目</th>
          <th width="150">金額</th>
        </tr>
      </thead>
      <tbody>
        <tr><th scope="row">売上</th>             <td class="text-end">{{ yen(row.sales_total) }}</td></tr>
        <tr><th scope="row">キャスト人件費</th>    <td class="text-end">{{ yen(row.cast_labor) }}</td></tr>
        <tr><th scope="row">ドライバー人件費</th> <td class="text-end">{{ yen(row.driver_labor) }}</td></tr>
        <tr><th scope="row">カスタム経費</th>      <td class="text-end">{{ yen(row.custom_expense) }}</td></tr>
      </tbody>
      <tfoot>
        <tr class="fw-bold"
            :class="row.gross_profit < 0 ? 'text-danger' : ''">
          <td class="text-center">粗利益</td>
          <td class="text-end">{{ yen(row.gross_profit) }}</td>
        </tr>
      </tfoot>
    </table>

    <div v-else class="text-muted">データ取得中…</div>
  </div>
</template>
