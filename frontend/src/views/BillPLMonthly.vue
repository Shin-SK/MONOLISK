<!-- src/views/BillPLMonthly.vue -->
<script setup>
import { ref, onMounted, watch } from 'vue'
import { getBillMonthlyPL, getBillMonthlyPLForStore } from '@/api'

const props = defineProps({
  storeIds: { type: Array, default: () => [] }
})

/* ---------- state ---------- */
const yearMonth   = ref(new Date().toISOString().slice(0, 7))  // 'YYYY-MM'
const rows        = ref([])    // 日別行
const total       = ref({})    // 月次合計
const loading     = ref(false) // ローディングフラグ
const yen         = n => `¥${(+n || 0).toLocaleString()}`      // undefined → 0

/* ---------- fetch ---------- */
async function fetchData() {
  loading.value = true
  const ids = (props.storeIds && props.storeIds.length) ? props.storeIds : []
  const storeId = localStorage.getItem('store_id')
  const finalIds = ids.length ? ids : (storeId ? [Number(storeId)] : [])

  if (finalIds.length > 1) {
    // 複数店舗：並列取得→合算
    const list = await Promise.all(
      finalIds.map(sid => getBillMonthlyPLForStore(yearMonth.value, sid, { cache:false }).catch(()=>({ days:[], monthly_total:{} })))
    )
    // 日別を日付でマージ
    const dayMap = new Map()
    for (const pl of list) {
      for (const d of (pl.days || [])) {
        if (!dayMap.has(d.date)) {
          dayMap.set(d.date, { date: d.date, sales_cash:0, sales_card:0, sales_total:0, cast_labor:0, gross_profit:0 })
        }
        const agg = dayMap.get(d.date)
        agg.sales_cash   += (Number(d.sales_cash) || 0)
        agg.sales_card   += (Number(d.sales_card) || 0)
        agg.sales_total  += (Number(d.sales_total) || 0)
        agg.cast_labor   += (Number(d.cast_labor) || 0)
        agg.gross_profit += (Number(d.gross_profit) || 0)
      }
    }
    rows.value = Array.from(dayMap.values()).sort((a,b) => a.date.localeCompare(b.date))

    // 月合計も合算
    const sum = (key) => list.reduce((a,b)=> a + (Number(b.monthly_total?.[key])||0), 0)
    total.value = {
      sales_cash   : sum('sales_cash'),
      sales_card   : sum('sales_card'),
      sales_total  : sum('sales_total'),
      cast_labor   : sum('cast_labor'),
      gross_profit : sum('gross_profit'),
    }
  } else {
    // 単店舗（既存）
    const { days, monthly_total } = await getBillMonthlyPL(yearMonth.value)
    rows.value   = days
    total.value  = monthly_total
  }
  loading.value = false
}

onMounted(fetchData)
watch(() => props.storeIds, fetchData, { deep: true })
</script>

<template>
  <div class="pl pl-monthly py-2">
    <!-- ── フィルタ ─────────────────────────────── -->
    <div class="row g-3 align-items-center mb-3">
      <div class="col-8">
        <input
          v-model="yearMonth"
          type="month"
          class="form-control w-100 bg-white"
        >
      </div>
      <div class="col-4">
          <button style="white-space: nowrap;"
          class="btn btn-sm btn-primary h-100 w-100"@click="fetchData">表示する</button>
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
        <div class="col-12 col-md-4">
          <div class="box">
            <div class="head">
              粗利益
            </div>
            <div class="number">
              {{ yen(total.gross_profit) }}
            </div>
          </div>
        </div>
        <div class="col-12 col-md-4">
          <div class="box">
            <div class="head">
              売上
            </div>
            <div class="number">
              {{ yen(total.sales_total) }}
            </div>
          </div>
        </div>
        <div class="col-12 col-md-4">
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

th{
  white-space: nowrap;
}

td{
  white-space: nowrap;
}

</style>