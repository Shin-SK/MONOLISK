<!-- src/views/BillPLMonthly.vue -->
<script setup>
import { ref, watchEffect } from 'vue'
import { getBillMonthlyPL }   from '@/api'

/* ---------- state ---------- */
const yearMonth   = ref(new Date().toISOString().slice(0, 7))  // 'YYYY-MM'
const rows        = ref([])    // 日別行
const total       = ref({})    // 月次合計
const loading     = ref(false) // ローディングフラグ
const yen         = n => `¥${(+n || 0).toLocaleString()}`      // undefined → 0

/* ---------- fetch ---------- */
watchEffect(async () => {
  loading.value = true
  const { days, monthly_total } = await getBillMonthlyPL(yearMonth.value)
  rows.value   = days
  total.value  = monthly_total
  loading.value = false
})
</script>

<template>
  <div class="pl pl-monthly container-fluid py-4">
    <!-- ── フィルタ ─────────────────────────────── -->
    <div class="d-flex gap-3 mb-3 align-items-end">
      <div>
        <label class="form-label small mb-1">対象月</label>
        <input
          v-model="yearMonth"
          type="month"
          class="form-control"
          style="max-width:180px"
        >
      </div>
    </div>

    <!-- ── 読み込み中 ────────────────────────────── -->
    <div v-if="loading">
      読み込み中…
    </div>

    <!-- ── 表示エリア ───────────────────────────── -->
    <template v-else>
      <!-- ▼ SUMMARY -->
      <div class="summary-area row g-3 mb-3">
        <div class="col-6 col-md-4">
          <div class="box">
            <div class="head">
              粗利益
            </div>
            <div class="number">
              {{ yen(total.gross_profit) }}
            </div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="box">
            <div class="head">
              売上
            </div>
            <div class="number">
              {{ yen(total.sales_total) }}
            </div>
          </div>
        </div>
        <div class="col-6 col-md-4">
          <div class="box">
            <div class="head">
              人件費
            </div><div class="number">
              {{ yen(total.cast_labor) }}
            </div>
          </div>
        </div>
      </div>

      <!-- ▼ TABLE -->
      <div class="table-responsive">
        <table class="table">
          <thead class="table-dark">
            <tr>
              <th>日付</th>
              <th class="text-end">現金</th>
              <th class="text-end">カード</th>
              <th class="text-end">売上（現金/カード）</th>
              <th class="text-end">キャスト</th>
              <th class="text-end">粗利益</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="d in rows"
              :key="d.date"
            >
              <td>{{ d.date }}</td>
              <td class="text-end">
                {{ yen(d.sales_cash) }}
              </td>
              <td class="text-end">
                {{ yen(d.sales_card) }}
              </td>
              <td class="text-end">
                <span class="fw-bold">{{ yen(d.sales_total) }}</span>
                ({{ yen(d.sales_cash) }}/{{ yen(d.sales_card) }})
              </td>
              <td class="text-end">
                {{ yen(d.cast_labor) }}
              </td>
              <td
                class="text-end fw-semibold"
                :class="{ 'text-danger': d.gross_profit < 0 }"
              >
                {{ yen(d.gross_profit) }}
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="table-secondary fw-bold">
              <td class="text-end">
                合計
              </td>
              <td class="text-end">
                {{ yen(total.sales_cash) }}
              </td>
              <td class="text-end">
                {{ yen(total.sales_card) }}
              </td>
              <td class="text-end">
                {{ yen(total.sales_total) }}({{ yen(total.sales_card) }}/{{ yen(total.sales_card) }})
              </td>
              <td class="text-end">
                {{ yen(total.cast_labor) }}
              </td>
              <td class="text-end">
                {{ yen(total.gross_profit) }}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </template>
  </div>
</template>


<style scoped>

.table > :not(caption) > * > * {
  padding: 1.5rem;
}

td{
  text-wrap: nowrap;
}

</style>