<script setup>
import { ref, onMounted, watch } from 'vue'
import { getStores, getDailyPL } from '@/api'
import dayjs from 'dayjs'
import { yen } from '@/utils/money'

const today  = dayjs().format('YYYY-MM-DD')
const date   = ref(today)
const store  = ref('')       // ← 初期化後に先頭店舗IDを自動セット
const stores = ref([])
const row    = ref(null)
const loading = ref(false)
const error   = ref('')

async function fetchStores () {
  stores.value = await getStores()
  // 日次は店舗必須。未選択なら先頭を自動選択
  if (!store.value && stores.value.length) {
    store.value = String(stores.value[0].id)
  }
}

async function fetchPL () {
  if (!store.value) return
  loading.value = true
  error.value = ''
  try {
    row.value = await getDailyPL(date.value, store.value)
  } catch (e) {
    error.value = '集計の取得に失敗しました'
    row.value = null
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchStores()
  await fetchPL()
})
watch([date, store], fetchPL)
</script>

<template>
  <div class="container py-4">
    <div class="text-muted small mb-2">※ 集計基準: 会計日（closed_at）</div>

    <!-- フィルタ -->
    <div class="d-flex gap-3 mb-4">
      <input v-model="date" type="date" class="form-control" style="max-width:180px">
      <select v-model="store" class="form-select" style="max-width:200px">
        <option value="" disabled>店舗を選択</option>
        <option v-for="s in stores" :key="s.id" :value="String(s.id)">
          {{ s.name }}
        </option>
      </select>
    </div>

    <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>

    <!-- 表 -->
    <table v-if="row && !loading" class="table table-striped w-100">
      <thead class="table-dark text-center">
        <tr><th width="130">項目</th><th width="150">金額</th></tr>
      </thead>
      <tbody>
        <tr><th scope="row">売上（現金）</th><td class="text-end">{{ yen(row.sales_cash) }}</td></tr>
        <tr><th scope="row">売上（カード）</th><td class="text-end">{{ yen(row.sales_card) }}</td></tr>
        <tr><th scope="row">売上（計）</th><td class="text-end">{{ yen(row.sales_total) }}</td></tr>
        <tr><th scope="row">キャスト人件費</th><td class="text-end">{{ yen(row.cast_labor) }}</td></tr>
        <tr><th scope="row">ドライバー人件費</th><td class="text-end">{{ yen(row.driver_labor) }}</td></tr>
        <tr><th scope="row">カスタム経費</th><td class="text-end">{{ yen(row.custom_expense) }}</td></tr>
      </tbody>
      <tfoot>
        <tr class="fw-bold" :class="row.gross_profit < 0 ? 'text-danger' : ''">
          <td>粗利益</td><td class="text-end">{{ yen(row.gross_profit) }}</td>
        </tr>
      </tfoot>
    </table>

<!-- 下段：会計内訳（カード/現金） -->
<div v-if="row && !loading" class="mt-4">
  <h6 class="fw-bold mb-2">会計内訳</h6>
  <div class="row g-3">
    <div class="col-sm-6">
      <div class="card h-100">
        <div class="card-body d-flex justify-content-between align-items-center">
          <div>カード会計</div>
          <!-- ここを null 合体で 0 に -->
          <div class="fs-5 fw-bold">{{ yen(row.sales_card ?? 0) }}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6">
      <div class="card h-100">
        <div class="card-body d-flex justify-content-between align-items-center">
          <div>現金会計</div>
          <!-- ここも同様に -->
          <div class="fs-5 fw-bold">{{ yen(row.sales_cash ?? 0) }}</div>
        </div>
      </div>
    </div>
  </div>
</div>

    <div v-else-if="loading" class="text-muted">データ取得中…</div>
  </div>
</template>
