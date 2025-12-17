<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { getHourlySales, getStore } from '@/api'
import { parseBusinessHours, hourToExtended, extendedToLabel, buildHourRange } from '@/utils/businessTime'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const props = defineProps({
  /**
   * 対象店舗ID（必須）
   * 例: "1"
   */
  storeId: { type: String, required: true },

  /**
   * グラフ対象の日付（YYYY-MM-DD、必須）
   * 例: "2025-12-17"
   */
  date: { type: String, required: true }
})

const hourlyData = ref([])
const isLoading = ref(false)
const storeInfo = ref(null) // 営業時間を取得するためのストア情報

/**
 * 単一店舗の時間帯別売上を取得・変換
 */
async function fetchHourly() {
  isLoading.value = true
  try {
    const { storeId, date } = props
    console.log('[HourlyChart] Fetching hourly data:', { storeId, date })

    if (!storeId || !date) {
      console.warn('[HourlyChart] Missing required props: storeId or date')
      hourlyData.value = []
      return
    }

    // 営業時間情報を取得（Store オブジェクトから）
    const storeData = await getStore(storeId).catch(() => null)
    if (storeData) {
      storeInfo.value = storeData
      console.log('[HourlyChart] Store info:', { store_id: storeData.id, business_hours: storeData.business_hours_display })
    }

    // 時間帯別売上を取得
    const rawData = await getHourlySales(date, storeId)
    console.log(`[HourlyChart] Hourly response for sid=${storeId}: ${Array.isArray(rawData) ? rawData.length : 0} items`)

    if (Array.isArray(rawData) && rawData.length > 0) {
      console.log(`  → First: hour=${rawData[0]?.hour}, sales=${rawData[0]?.sales_total}`)
      const totalSales = rawData.reduce((sum, item) => sum + (item?.sales_total ?? 0), 0)
      console.log(`  → Total sales: ${totalSales}`)
    }

    // 営業時間を取得（デフォルト: 9:00-23:00）
    const { openHour, closeHour } = storeInfo.value
      ? parseBusinessHours(storeInfo.value)
      : { openHour: 9, closeHour: 23 }

    console.log('[HourlyChart] Business hours:', { openHour, closeHour })

    // hour(0-23) を拡張時刻にマッピング
    const hourlyMap = new Map()
    if (Array.isArray(rawData)) {
      rawData.forEach(item => {
        const hour = Number(item?.hour ?? 0)
        const sales_total = Number(item?.sales_total ?? 0)
        const extendedHour = hourToExtended(hour, openHour)
        hourlyMap.set(extendedHour, { extendedHour, sales_total })
      })
    }

    // 営業時間範囲内の拡張時刻配列を生成
    const hourRange = buildHourRange(openHour, closeHour)
    const normalized = hourRange.map(extH => 
      hourlyMap.get(extH) || { extendedHour: extH, sales_total: 0 }
    )

    hourlyData.value = normalized
  } catch (e) {
    const status = e?.response?.status
    const url = e?.config?.url
    console.error('[HourlyChart] Failed to fetch hourly data:', { status, url, error: e?.message })
    hourlyData.value = []
  } finally {
    isLoading.value = false
  }
}

/**
 * グラフデータを生成（営業時間範囲内で拡張時刻ラベル付き）
 */
const chartData = computed(() => {
  if (!Array.isArray(hourlyData.value) || hourlyData.value.length === 0) {
    return { labels: [], datasets: [] }
  }

  const labels = hourlyData.value.map(item => 
    extendedToLabel(item?.extendedHour ?? 0)
  )
  const data = hourlyData.value.map(item => Number(item?.sales_total ?? 0))

  return {
    labels,
    datasets: [
      {
        label: '売上',
        data,
        backgroundColor: 'rgba(64, 150, 255, 0.8)',
        borderColor: 'rgba(24, 144, 255, 1)',
        borderWidth: 1,
        borderRadius: 4,
        hoverBackgroundColor: 'rgba(105, 177, 255, 0.9)',
      }
    ]
  }
})

const chartHeight = computed(() => {
  const hourCount = hourlyData.value.length || 8
  const dynamicHeight = Math.max(300, hourCount * 35)
  return `${dynamicHeight}px`
})

const chartOptions = computed(() => ({
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const value = context.parsed.x
          return `売上: ¥${value.toLocaleString()}`
        }
      }
    }
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: { color: '#f0f0f0' },
      ticks: {
        callback: (value) => {
          if (value === 0) return '¥0'
          if (value >= 1000000) return `¥${(value / 1000000).toFixed(0)}M`
          if (value >= 10000) return `¥${(value / 10000).toFixed(0)}万`
          if (value >= 1000) return `¥${(value / 1000).toFixed(0)}K`
          return `¥${value}`
        }
      }
    },
    y: {
      grid: { display: false }
    }
  }
}))

onMounted(() => {
  fetchHourly()
})

// storeId または date が変わったら再取得
watch([() => props.storeId, () => props.date], () => {
  fetchHourly()
})
</script>

<template>
  <div class="hourly-chart">
    <div v-if="isLoading" class="loading-message">
      読み込み中...
    </div>
    <div v-else-if="!hourlyData || hourlyData.length === 0" class="no-data-message">
      時間別データがありません
    </div>

    <Bar
      v-else
      :data="chartData"
      :options="chartOptions"
      :style="{ width: '100%', height: chartHeight }"
    />
  </div>
</template>

<style scoped>
.hourly-chart {
  width: 100%;
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  min-height: 300px;
}

.loading-message {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 250px;
  color: #999;
  font-size: 14px;
}

.no-data-message {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 250px;
  color: #999;
  font-size: 14px;
}
</style>
