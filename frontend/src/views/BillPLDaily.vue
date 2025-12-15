<!-- BillPLDaily.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { getBillDailyPL, getStores, getHourlySales, getStore } from '@/api'
import HourlyChart from '@/components/HourlyChart.vue'

const dateStr = ref(new Date().toISOString().slice(0, 10))
const pl      = ref(null)
const hourlyData = ref([])
const store   = ref(null)
const openingHour = ref(9)
const closingHour = ref(23)

// ★ 追加: 未定義だった変数を定義
const stores  = ref([])
const storeId = ref(localStorage.getItem('store_id')
  ? Number(localStorage.getItem('store_id'))
  : null)

const yen = n => `¥${(+n || 0).toLocaleString()}`

async function fetchData () {
  // PL情報を取得
  pl.value = await getBillDailyPL(dateStr.value, storeId.value)
  
  // ★ バックエンドから時間別売上データを取得
  try {
    const data = await getHourlySales(dateStr.value, storeId.value)
    hourlyData.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.warn('[BillPLDaily] Failed to fetch hourly sales:', e)
    hourlyData.value = []
  }
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

// ★ 追加: Store 詳細情報を取得（営業時間を含む）
async function loadStoreDetail () {
  if (!storeId.value) return
  try {
    // キャッシュを使わないようにタイムスタンプを追加
    store.value = await getStore(storeId.value)
    console.log('[BillPLDaily] Store loaded:', store.value)
    
    // ★ business_hours_display から営業時間を抽出
    if (store.value?.business_hours_display) {
      // 例: "20:00-翌03:00" → opening: 20, closing: 27 (3+24)
      // 例: "09:00-23:00" → opening: 9, closing: 23
      const match = store.value.business_hours_display.match(/(\d{2}):(\d{2})-(?:翌)?(\d{2}):(\d{2})/)
      if (match) {
        const openH = parseInt(match[1], 10)
        let closeH = parseInt(match[3], 10)
        
        // 「翌」が含まれていれば、翌日扱い（24時間加算）
        if (store.value.business_hours_display.includes('翌')) {
          closeH += 24
        }
        
        openingHour.value = openH
        closingHour.value = closeH
        console.log('[BillPLDaily] Parsed hours - opening:', openH, 'closing:', closeH)
      }
    }
  } catch (e) {
    console.warn('[BillPLDaily] Failed to fetch store detail:', e)
    store.value = null
  }
}

onMounted(async () => {
  await loadStores()
  await loadStoreDetail()
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

      <div class="graph">
        <!-- 時間帯別売上グラフ（バックエンドから取得） -->
        <HourlyChart 
          :hourly-data="hourlyData"
          :opening-hour="openingHour"
          :closing-hour="closingHour"
          :business-hours-display="store?.business_hours_display"
        />
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
