<!-- src/components/charts/CastRankBar.vue -->
<script setup>
import { ref, computed } from 'vue'

const el = ref(null)
defineExpose({                       // ← 追加：親からresizeできるよう公開
  resize: () => el.value?.resize?.()
})

const props = defineProps({
  rows: { type: Array, required: true }, // [{stage_name, revenue}, ...]
  height: { type: String, default: '360px' },
  top: { type: Number, default: 10 },
})
const topRows = computed(() => props.rows.slice(0, props.top))
const option = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 120, right: 24, top: 10, bottom: 24 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: topRows.value.map(r => r.stage_name) },
  series: [{ type: 'bar', data: topRows.value.map(r => r.revenue) }],
}))
</script>

<template>
   <VChart ref="el" :option="option" :style="{ height, width:'100%' }" autoresize />
</template>
