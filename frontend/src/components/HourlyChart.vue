<script setup>
import { ref, computed } from 'vue'
import VChart from 'vue-echarts'
import * as echarts from 'echarts'

const props = defineProps({
  // バックエンドから取得した時間別売上データ（0時～23時の24時間）
  // 構造: [{ hour: 0, sales_total: 0, ... }, { hour: 1, sales_total: 500000 }, ...]
  hourlyData: { type: Array, default: () => [] },
  // 営業開始時刻（24時間制: 0-23）
  openingHour: { type: Number, default: 9 },
  // 営業終了時刻（24時間制: 0-23。例: 23時まで営業 or 翌5時までなら 5+24=29）
  closingHour: { type: Number, default: 23 },
  // 営業時間表示（例: "20:00-翌03:00"）
  businessHoursDisplay: { type: String, default: '' },
})

const chartRef = ref(null)

// グラフ用にデータを整形（営業時間で絞る）
const chartData = computed(() => {
  if (!Array.isArray(props.hourlyData) || props.hourlyData.length === 0) {
    return { hours: [], sales: [] }
  }

  console.log('[HourlyChart] openingHour:', props.openingHour, 'closingHour:', props.closingHour)
  
  const hours = []
  const sales = []

  // 営業時間内のデータのみを抽出
  for (let h = props.openingHour; h < props.closingHour; h++) {
    // 該当する時間のデータを探す
    const item = props.hourlyData.find(d => d.hour === h)
    hours.push(`${String(h).padStart(2, '0')}:00`)
    sales.push(item ? (item.sales_total || 0) : 0)
  }

  console.log('[HourlyChart] chartData hours:', hours.length, '最初:', hours[0], '最後:', hours[hours.length - 1])

  return { hours, sales }
})

// Y軸のカスタム目盛り値
const yAxisValues = [1000000, 500000, 200000, 100000, 50000, 30000, 10000, 5000, 1000]

// ECharts オプション
const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    formatter: (params) => {
      if (!params || !params.length) return ''
      const { name, value } = params[0]
      return `${name}<br/>売上: ¥${value.toLocaleString()}`
    },
  },
  grid: {
    left: '10%',
    right: '5%',
    bottom: '15%',
    top: '10%',
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: chartData.value.hours,
    boundaryGap: true,
  },
  yAxis: {
    type: 'value',
    // Y軸の目盛りをカスタム設定
    min: 0,
    // max は自動（データに合わせて拡張）
    splitLine: {
      show: true,
      lineStyle: {
        color: '#f0f0f0',
      },
    },
    axisLabel: {
      formatter: (v) => {
        if (v === 0) return '¥0'
        if (v >= 1000000) return `¥${(v / 1000000).toFixed(0)}M`
        if (v >= 10000) return `¥${(v / 10000).toFixed(0)}万`
        return `¥${(v / 1000).toFixed(0)}K`
      },
    },
  },
  series: [
    {
      type: 'bar',
      data: chartData.value.sales,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#4096ff' },
          { offset: 1, color: '#1890ff' },
        ]),
      },
      emphasis: {
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#69b1ff' },
            { offset: 1, color: '#40a9ff' },
          ]),
        },
      },
      label: {
        show: false,
      },
    },
  ],
}))
</script>

<template>
  <div class="hourly-chart">
    <v-chart
      ref="chartRef"
      :option="chartOption"
      style="width: 100%; height: 300px;"
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
}
</style>
