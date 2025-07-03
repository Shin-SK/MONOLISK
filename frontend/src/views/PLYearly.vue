<!-- src/views/Yearly.vue -->
<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { getStores, getYearlyPL } from '@/api'
import { yen } from '@/utils/money'

/* ---------- state ---------- */
const year   = ref(new Date().getFullYear())
const store  = ref('')
const stores = ref([])
const months = ref([])

/* ---------- fetch ---------- */
const fetchStores = async () => { stores.value = await getStores() }
const fetchYearly = async () => {
  months.value = (await getYearlyPL(year.value, store.value)).months
}

/* ★ 全月に登場する固定費ラベルをユニーク抽出 */
const fixedLabels = computed(() => {
  const set = new Set()
  months.value.forEach(m =>
    (m.fixed_breakdown ?? []).forEach(f => set.add(f.name))
  )
  return Array.from(set)
})

onMounted(async () => { await fetchStores(); await fetchYearly() })
watch([year, store], fetchYearly)
</script>

<template>
<div class="container-fluid py-4">
  <h1 class="h4 mb-3">{{ year }}年 P/L</h1>

  <!-- フィルタ -->
  <div class="d-flex gap-3 mb-3 align-items-end">
    <div>
      <label class="form-label small mb-1">年度</label>
      <input type="number" v-model.number="year" class="form-control" style="max-width:120px">
    </div>
    <div>
      <label class="form-label small mb-1">店舗</label>
      <select v-model="store" class="form-select" style="max-width:200px">
        <option value="">全店舗</option>
        <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>
  </div>


  <!-- 月別テーブル -->
  <div class="table-responsive">
    <table class="table table-sm align-middle table-striped">
      <thead class="table-dark">
        <tr>
          <th>月</th>
          <th class="text-end">売上</th>
          <th class="text-end">キャスト人件費</th>
          <th class="text-end">ドライバー人件費</th>

          <!-- 固定費ラベルを列ヘッダに -->
          <th v-for="l in fixedLabels" :key="l" class="text-end">{{ l }}</th>

          <th class="text-end">カスタム経費</th>
          <th class="text-end">営業利益</th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="m in months" :key="m.month">
          <td>{{ m.month.split('-')[1] }}月</td>
          <td class="text-end">{{ yen(m.sales_total) }}</td>
          <td class="text-end">{{ yen(m.cast_labor) }}</td>
          <td class="text-end">{{ yen(m.driver_labor) }}</td>

          <!-- ラベルごとの固定費 -->
          <td v-for="l in fixedLabels" :key="l" class="text-end">
            {{ yen((m.fixed_breakdown ?? []).find(f => f.name === l)?.amount ?? 0) }}
          </td>

          <td class="text-end">{{ yen(m.custom_expense) }}</td>
          <td class="text-end fw-semibold"
              :class="m.operating_profit < 0 ? 'text-danger' : ''">
            {{ yen(m.operating_profit) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>

</div>
</template>

<style scoped>
.table-responsive { max-height: 70vh; }
</style>
