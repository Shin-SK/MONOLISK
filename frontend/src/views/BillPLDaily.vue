<!-- BillPLDaily.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { getBillDailyPL, getStores } from '@/api'

const dateStr = ref(new Date().toISOString().slice(0, 10))
const pl      = ref(null)

// ★ 追加: 未定義だった変数を定義
const stores  = ref([])
const storeId = ref(localStorage.getItem('store_id')
  ? Number(localStorage.getItem('store_id'))
  : null)

const yen = n => `¥${(+n || 0).toLocaleString()}`

async function fetchData () {
  // storeId を渡す（Interceptor があるので null でもOK）
  pl.value = await getBillDailyPL(dateStr.value, storeId.value)
}

async function loadStores () {
  // すでに store_id があれば取得不要
  if (storeId.value) return
  try {
    const data = await getStores()
    const list = Array.isArray(data?.results) ? data.results
               : Array.isArray(data) ? data
               : []
    stores.value  = list
    storeId.value = list[0]?.id ?? null
    if (storeId.value) localStorage.setItem('store_id', String(storeId.value))
  } catch (e) {
    // 取得失敗しても user.store 側で Store-Locked される想定なので続行
  }
}

onMounted(async () => {
  await loadStores()
  await fetchData()
})
</script>

<template>
  <div class="pl pl-daily py-2">
    <template v-if="pl">
      <div class="row g-2 align-items-center mb-3">
        <div class="col-8">
          <input v-model="dateStr" type="date" class="form-control w-100 bg-white">
        </div>
        <div class="col-4 h-100">
          <button
          style="white-space: nowrap;"
          class="btn btn-sm btn-primary h-100 w-100" @click="fetchData">表示する</button>
        </div>
      </div>

      <div class="summary-area row g-3">
        <div class="col-12 col-md-4">
          <div class="box">
            <div class="head">売上合計</div>
            <div class="number">{{ yen(pl.sales_total ?? ((pl.sales_cash ?? 0) + (pl.sales_card ?? 0))) }}</div>
          </div>
        </div>
        <div class="col-12 col-md-4">
          <div class="box">
            <div class="head">人件費</div>
            <div class="number">{{ yen(pl.labor_cost) }}</div>
          </div>
        </div>
        <div class="col-12 col-md-4">
          <div class="box">
            <div class="head">営業利益</div>
            <div class="number">{{ yen(pl.operating_profit) }}</div>
          </div>
        </div>
      </div>

      <table class="table no-vert my-5">
        <tbody>
          <tr><th>来客数</th><td class="text-end">{{ pl.guest_count }}</td></tr>
          <tr><th>平均客単価</th><td class="text-end">{{ yen(pl.avg_spend) }}</td></tr>
          <tr><th>ドリンク売上</th><td class="text-end">{{ yen(pl.drink_sales) }}</td></tr>
          <tr><th>ドリンク杯数</th><td class="text-end">{{ pl.drink_qty }}</td></tr>
          <tr><th>ドリンク単価</th><td class="text-end">{{ yen(pl.drink_unit_price) }}</td></tr>
          <tr><th>延長回数</th><td class="text-end">{{ pl.extension_qty }}</td></tr>
          <tr><th>VIP比率</th><td class="text-end">{{ (pl.vip_ratio * 100).toFixed(1) }}%</td></tr>
        </tbody>
      </table>

      <!-- ▼ 追加：会計内訳（必ず0円表示） -->
      <div class="mt-4">
        <h6 class="fw-bold mb-3">会計内訳</h6>
        <div class="row g-3">
          <div class="col-mb-6">
            <div class="h-100">
              <div class="bg-white d-flex justify-content-between align-items-center p-3">
                <div>カード会計</div>
                <div class="fs-5 fw-bold">{{ yen(pl.sales_card ?? 0) }}</div>
              </div>
            </div>
          </div>
          <div class="col-mb-6">
            <div class="h-100">
              <div class="bg-white d-flex justify-content-between align-items-center p-3">
                <div>現金会計</div>
                <div class="fs-5 fw-bold">{{ yen(pl.sales_cash ?? 0) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- ▲ ここまで追加 -->
    </template>

    <div v-else class="text-muted">読み込み中…</div>
  </div>
</template>

<style scoped>
.pl-daily input,
.pl-daily select { min-width: 130px; }

.table > :not(caption) > * > * {
  padding: 1.5rem;
}

td{
  text-wrap: nowrap;
}
.table.no-vert > :not(caption) > * > * {
  border-left: 0 !important;
  border-right: 0 !important;
}


</style>
