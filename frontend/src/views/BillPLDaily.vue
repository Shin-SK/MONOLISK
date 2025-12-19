<!-- BillPLDaily.vue -->
<script setup>
import { ref, onMounted, watch } from 'vue'
import { getBillDailyPL, getBillDailyPLForStore, getStores, getHourlySales, getStore } from '@/api'
import HourlyChart from '@/components/HourlyChart.vue'
import MiniTip from '@/components/MiniTip.vue'
import {
  parseBusinessHours,
  displayRangeFromStores
} from '@/utils/businessTime'

const props = defineProps({
  storeIds: { type: Array, default: () => [] }
})

const dateStr = ref(new Date().toISOString().slice(0, 10))
const pl      = ref(null)
const hourlyData = ref([])

// グラフ表示レンジ
const displayRange = ref({ openingHour: 9, closingHour: 23, hours: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22] })

// HourlyChart 用（fetchData で決定される店舗ID）
const selectedStoreIdsForGraph = ref([])

// 店舗情報
const stores  = ref([])
const storeId = ref(localStorage.getItem('store_id')
  ? Number(localStorage.getItem('store_id'))
  : null)

// ツールチップ表示フラグ
const showOpenTipSalesAve = ref(false)
const showOpenTipDrinkAve = ref(false)
const showOpenTipEx = ref(false)

const yen = n => `¥${(+n || 0).toLocaleString()}`

/**
 * 複数店舗の hourly データを hour(0-23) 単位で合算
 * 
 * @param {Array} hourlyArrays - 店舗ごとの hourly 配列群
 *   例: [[{hour:0, sales_total:1000, ...}, ...], [{hour:0, sales_total:500, ...}, ...]]
 * @returns {Array} hour(0-23) をキーに合算した配列
 *   例: [{hour:0, sales_total:1500, ...}, {hour:1, sales_total:xxx, ...}, ...]
 */
function mergeHourlyByHour(hourlyArrays) {
  const hourlyMap = new Map()

  // 各店舗の配列を合算
  hourlyArrays.forEach((hourlyArray, storeIndex) => {
    if (!Array.isArray(hourlyArray)) return

    hourlyArray.forEach(item => {
      const hour = Number(item?.hour ?? 0)
      const sales_total = Number(item?.sales_total ?? 0)
      const bill_count = Number(item?.bill_count ?? 0)
      const customer_count = Number(item?.customer_count ?? 0)

      const key = hour
      const existing = hourlyMap.get(key) || {
        hour,
        sales_total: 0,
        bill_count: 0,
        customer_count: 0
      }

      hourlyMap.set(key, {
        hour,
        sales_total: existing.sales_total + sales_total,
        bill_count: existing.bill_count + bill_count,
        customer_count: existing.customer_count + customer_count
      })
    })
  })

  // Map を 0..23 順の配列に変換
  const merged = []
  for (let h = 0; h < 24; h++) {
    merged.push(hourlyMap.get(h) || { hour: h, sales_total: 0, bill_count: 0, customer_count: 0 })
  }

  return merged
}

/**
 * メイン fetchData：P&L + hourly データ取得（複数店舗対応）
 */
async function fetchData() {
  // storeIds の取得・正規化
  const rawIds = (props.storeIds && props.storeIds.length) ? props.storeIds : (storeId.value ? [storeId.value] : [])
  const ids = rawIds
    .map(v => {
      const n = Number(v)
      return Number.isFinite(n) ? n : String(v)
    })
    .filter(v => v !== '' && v != null)

  console.log('[BillPLDaily] fetchData - rawIds:', rawIds, 'resolved ids:', ids)

  // ★ HourlyChart 用に store ID を保存
  selectedStoreIdsForGraph.value = ids

  // ================== 1) PL データ取得 ==================
  if (ids.length > 1) {
    // 複数店舗：並列取得→合算
    await fetchMultiStorePL(ids)
  } else {
    // 単一店舗
    const sid = ids[0] || storeId.value
    try {
      pl.value = await getBillDailyPLForStore(dateStr.value, sid, { cache: false })
      console.log('[BillPLDaily] Single-store PL loaded, sid:', sid, 'sales_total:', pl.value?.sales_total)
    } catch (e) {
      console.error('[BillPLDaily] Failed to fetch PL for single store', { sid, error: e?.message })
      pl.value = null
    }
  }

  // ================== 2) 時間別売上取得（複数店舗並列） ==================
  await fetchHourlyForSelectedStores(ids)

  // ================== 3) グラフ表示レンジを計算 ==================
  await calculateDisplayRange(ids)
}

/**
 * 複数店舗の PL 合算
 */
async function fetchMultiStorePL(storeIds) {
  try {
    const list = await Promise.all(
      storeIds.map(sid => getBillDailyPLForStore(dateStr.value, sid, { cache: false }).catch(() => ({})))
    )
    const sum = (key) => list.reduce((a, b) => a + (Number(b?.[key]) || 0), 0)
    pl.value = {
      sales_total      : sum('sales_total'),
      sales_cash       : sum('sales_cash'),
      sales_card       : sum('sales_card'),
      guest_count      : sum('guest_count'),
      avg_spend        : sum('sales_total') / (sum('guest_count') || 1),
      cast_hourly      : sum('cast_hourly'),
      cast_commission  : sum('cast_commission'),
      cast_labor       : sum('cast_labor'),
      labor_cost       : sum('labor_cost'),
      operating_profit : sum('operating_profit'),
      drink_sales      : sum('drink_sales'),
      drink_qty        : sum('drink_qty'),
      drink_unit_price : sum('drink_sales') / (sum('drink_qty') || 1),
      champagne_sales  : sum('champagne_sales'),
      champagne_qty    : sum('champagne_qty'),
      extension_sales  : sum('extension_sales'),
      extension_qty    : sum('extension_qty'),
      other_sales      : sum('other_sales'),
      vip_ratio        : list.length ? list.reduce((a, b) => a + (Number(b?.vip_ratio) || 0), 0) / list.length : 0,
    }
    console.log('[BillPLDaily] Multi-store PL aggregated, total sales:', pl.value?.sales_total)
  } catch (e) {
    console.error('[BillPLDaily] Failed to fetch multi-store PL:', e)
    pl.value = null
  }
}

/**
 * 選択店舗ごとに hourly を取得 → hour(0-23) 単位で合算
 */
async function fetchHourlyForSelectedStores(storeIds) {
  try {
    if (!Array.isArray(storeIds) || storeIds.length === 0) {
      hourlyData.value = []
      return
    }

    // 各店舗の hourly を並列取得
    const hourlyArrays = await Promise.all(
      storeIds.map(async (sid) => {
        try {
          const data = await getHourlySales(dateStr.value, sid)
          console.log(`[BillPLDaily] Hourly response for sid=${sid}: ${data?.length ?? 0} items`)
          if (Array.isArray(data) && data.length > 0) {
            console.log(`  → First item: hour=${data[0]?.hour}, sales=${data[0]?.sales_total}`)
          }
          return Array.isArray(data) ? data : []
        } catch (e) {
          const status = e?.response?.status
          const url = e?.config?.url
          console.error('[BillPLDaily] Hourly fetch failed for sid=' + sid, { status, url, error: e?.message })
          return []
        }
      })
    )

    // hour(0-23) 単位で合算
    const mergedHourly = mergeHourlyByHour(hourlyArrays)

    // 検証ログ：合算結果の確認
    const totalHourlySales = mergedHourly.reduce((sum, item) => sum + (item?.sales_total ?? 0), 0)
    console.log('[BillPLDaily] Merged hourly - total sales:', totalHourlySales, 'vs PL sales_total:', pl.value?.sales_total)

    hourlyData.value = mergedHourly
    console.log('[BillPLDaily] Hourly aggregation complete, hours:', mergedHourly.length)
  } catch (e) {
    console.error('[BillPLDaily] Failed to fetch hourly data:', e)
    hourlyData.value = []
  }
}

/**
 * グラフ表示レンジを計算（選択店舗の営業時間から min-max を取得）
 */
async function calculateDisplayRange(storeIds) {
  try {
    if (!Array.isArray(storeIds) || storeIds.length === 0) {
      displayRange.value = { openingHour: 9, closingHour: 23, hours: Array.from({length: 14}, (_, i) => 9 + i) }
      return
    }

    // 各店舗の store 情報を取得
    const storeDetails = await Promise.all(
      storeIds.map(sid => getStore(sid).catch(() => null))
    ).then(results => results.filter(Boolean))

    // 営業時間範囲を計算
    const range = displayRangeFromStores(storeDetails)
    displayRange.value = range

    console.log('[BillPLDaily] Display range calculated:', {
      openingHour: range.openingHour,
      closingHour: range.closingHour,
      hours: range.hours.length
    })
  } catch (e) {
    console.warn('[BillPLDaily] Failed to calculate display range:', e)
  }
}

async function loadStores () {
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
    console.warn('[BillPLDaily] Failed to load stores:', e)
  }
}

onMounted(async () => {
  await loadStores()
  await fetchData()
})

// storeIds の変更を監視
watch(() => props.storeIds, fetchData, { deep: true })

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
            <div class="head">人件費<small>（時給＋歩合）</small></div>
            <div class="number">{{ yen(pl.cast_labor ?? pl.labor_cost) }}</div>
          </div>
        </div>
        <div class="col-12 col-md-4">
          <div class="box">
            <div class="head">営業利益</div>
            <div class="number">{{ yen(pl.operating_profit) }}</div>
          </div>
        </div>
      </div>

      <!-- <div class="graph">
        
        <HourlyChart 
          :selected-store-ids="selectedStoreIdsForGraph"
          :date="dateStr"
        />
      </div> -->

      <!-- ▼ 追加：会計内訳（必ず0円表示） -->
      <div class="mt-4">
        <h6 class="fw-bold mb-3">会計内訳</h6>
        <div class="row g-3">
          <div class="col-12">
              <div class="h-100">
                <div class="bg-white d-flex justify-content-between align-items-center p-3">
                  <div class="fw-bold">売上合計</div>
                  <div class="fs-5 fw-bold">{{ yen(pl.sales_total ?? ((pl.sales_cash ?? 0) + (pl.sales_card ?? 0))) }}</div>
                </div>
              </div>          
          </div>
          <div class="col-mb-6">
            <div class="h-100">
              <div class="bg-white d-flex justify-content-between align-items-center p-3">
                <div class="ps-3">カード会計</div>
                <div class="">{{ yen(pl.sales_card ?? 0) }}</div>
              </div>
            </div>
          </div>
          <div class="col-mb-6">
            <div class="h-100">
              <div class="bg-white d-flex justify-content-between align-items-center p-3">
                <div class="ps-3">現金会計</div>
                <div class="">{{ yen(pl.sales_cash ?? 0) }}</div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <div class="mt-5">
        <h6 class="fw-bold mb-3">収支</h6>
        <table class="table no-vert mb-5">
          <tbody>
            <tr class="text-blue border-top"><th>売上</th><td class="text-end fw-bold">{{ yen(pl.sales_total ?? ((pl.sales_cash ?? 0) + (pl.sales_card ?? 0))) }}</td></tr>
            <tr class="text-blue"><th>来客数</th><td class="text-end">{{ pl.guest_count }}</td></tr>
            <tr class="text-blue">
              <th>
                <div class="d-flex align-items-center gap-1">
                  平均客単価
                  <MiniTip v-model="showOpenTipSalesAve" text="平均値 / 人数" align="right">
                    <button type="button" class="btn btn-link p-0 text-muted d-flex align-items-center" @click.stop="showOpenTipSalesAve = !showOpenTipSalesAve">
                      <IconInfoCircle />
                    </button>
                  </MiniTip>
                </div>
              </th>
              <td class="text-end">{{ yen(pl.avg_spend) }} / {{ pl.guest_count }}</td>
            </tr>
            <tr class="text-blue"><th>ドリンク売上</th><td class="text-end">{{ yen(pl.drink_sales) }}</td></tr>
            <tr class="text-blue">
              <th>
                <div class="d-flex align-items-center gap-1">
                  ドリンク平均単価
                  <MiniTip v-model="showOpenTipDrinkAve" text="平均値 / 杯数" align="right">
                    <button type="button" class="btn btn-link p-0 text-muted d-flex align-items-center" @click.stop="showOpenTipDrinkAve = !showOpenTipDrinkAve">
                      <IconInfoCircle />
                    </button>
                  </MiniTip>
                </div>
              </th>
              <td class="text-end">{{ yen(pl.drink_unit_price) }} / {{ pl.drink_qty }}</td>
            </tr>
            <tr class="text-blue"><th>シャンパン売上</th><td class="text-end">{{ yen(pl.champagne_sales ?? 0) }}</td></tr>
            <tr class="text-blue">
              <th>
                <div class="d-flex align-items-center gap-1">
                    延長売上
                  <MiniTip v-model="showOpenTipEx" text="売上 / 人数" align="right">
                    <button type="button" class="btn btn-link p-0 text-muted d-flex align-items-center" @click.stop="showOpenTipEx = !showOpenTipEx">
                      <IconInfoCircle />
                    </button>
                  </MiniTip>
                </div>            </th>
              <td class="text-end">{{ yen(pl.extension_sales ?? 0) }} / {{ pl.extension_qty ?? 0 }}</td>
            </tr>
            <tr class="text-blue"><th>その他売上</th><td class="text-end">{{ yen(pl.other_sales ?? 0) }}</td></tr>
            <tr class="text-red"><th>人件費（合算）</th><td class="text-end fw-bold">{{ yen(pl.cast_labor ?? pl.labor_cost ?? 0) }}</td></tr>
            <tr class="text-red"><th class="fw-normal ps-5">時給</th><td class="text-end">{{ yen(pl.cast_hourly ?? pl.hourly_pay ?? 0) }}</td></tr>
            <tr class="text-red"><th class="fw-normal ps-5">歩合</th><td class="text-end">{{ yen(pl.cast_commission ?? pl.commission ?? 0) }}</td></tr>
            <tr><th>営業利益</th><td class="text-end fw-bold fs-5">{{ yen(pl.operating_profit ?? 0) }}</td></tr>
          </tbody>
        </table>
      </div>


      <!-- ▲ ここまで追加 -->
    </template>

    <div v-else class="text-muted">読み込み中…</div>
  </div>
</template>

<style scoped>
.table .text-blue{
  --bs-table-color: #0051c9 !important;
}
.table .text-red{
  --bs-table-color: #bb0012 !important;
}
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
