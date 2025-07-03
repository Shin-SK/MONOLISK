<script setup>
import { ref, watch, onMounted } from 'vue'
import { getStores, getMonthlyPL } from '@/api'

/* ────────── 入力（年月・店舗） ────────── */
// 「2025-07」のような文字列で保持（<input type="month"> と相性が良い）
const yearMonth = ref(new Date().toISOString().slice(0,7))
const store     = ref('')                // ''=全店舗
const stores    = ref([])                // 店舗プルダウン

/* ────────── 出力 ────────── */
const rows      = ref([])                // 日次配列
const total     = ref({                  // 合計行
  sales_total: 0,
  cast_labor: 0,
  driver_labor: 0,
  custom_expense: 0,
  gross_profit: 0,
})

/* ────────── 初期ロード ────────── */
async function fetchStores () {
  stores.value = await getStores()
}

async function fetchData () {
  const data = await getMonthlyPL(yearMonth.value, store.value)
  rows.value  = data.days
  total.value = data.monthly_total
}

onMounted(async () => {
  await fetchStores()
  await fetchData()
})

// 入力が変わったら自動再読込
watch([yearMonth, store], fetchData)
</script>

<template>
<div class="pl pl-monthly container-fluid py-4">
  <h1 class="h4 mb-3">月次P/L</h1>


  <div class="summary-area">

    <div class="box">
      <div class="head">粗利益</div>
      <div class="number">{{ $yen(total.gross_profit) }}</div>
    </div>

    <div class="box">
      <div class="head">売上</div>
      <div class="number">{{ $yen(total.sales_total) }}</div>
    </div>

    <div class="box">
      <div class="head">キャスト人件費</div>
      <div class="number">{{ $yen(total.cast_labor) }}</div>
    </div>

    <div class="box">
      <div class="head">ドライバー人件費</div>
      <div class="number">{{ $yen(total.driver_labor) }}</div>
    </div>

    <div class="box">
      <div class="head">カスタム経費</div>
      <div class="number">{{ $yen(total.custom_expense) }}</div>
    </div>

  </div>
  <!-- フィルタ UI -->
  <div class="d-flex gap-3 mb-3 align-items-end">
    <div>
      <label class="form-label small mb-1">対象月</label>
      <input type="month" v-model="yearMonth" class="form-control" style="max-width:180px">
    </div>
    <div>
      <label class="form-label small mb-1">店舗</label>
      <select v-model="store" class="form-select" style="max-width:200px">
        <option value="">全店舗</option>
        <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>
  </div>

  <!-- 明細テーブル -->
  <div class="table-responsive">
    <table class="table table-sm align-middle table-striped">
      <thead class="table-dark">
        <tr>
          <th class="text-nowrap">日付</th>
          <th class="text-end">売上</th>
          <th class="text-end">キャスト人件費</th>
          <th class="text-end">ドライバー人件費</th>
          <th class="text-end">カスタム経費</th>
          <th class="text-end">粗利益</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in rows" :key="d.date">
          <td class="text-nowrap">{{ d.date }}</td>
          <td class="text-end">{{ $yen(d.sales_total) }}</td>
          <td class="text-end">{{ $yen(d.cast_labor) }}</td>
          <td class="text-end">{{ $yen(d.driver_labor) }}</td>
          <td class="text-end">{{ $yen(d.custom_expense) }}</td>
          <td class="text-end fw-semibold" :class="d.gross_profit < 0 ? 'text-danger' : ''">
            {{ $yen(d.gross_profit) }}
          </td>
        </tr>
      </tbody>
      <!-- 合計行 -->
      <tfoot>
        <tr class="table-secondary fw-bold">
          <td class="text-end">合計</td>
          <td class="text-end">{{ $yen(total.sales_total) }}</td>
          <td class="text-end">{{ $yen(total.cast_labor) }}</td>
          <td class="text-end">{{ $yen(total.driver_labor) }}</td>
          <td class="text-end">{{ $yen(total.custom_expense) }}</td>
          <td class="text-end">{{ $yen(total.gross_profit) }}</td>
        </tr>
      </tfoot>
    </table>
  </div>
</div>
</template>

