<script setup>
import { ref, computed, defineAsyncComponent } from 'vue'

const VChartLocal = defineAsyncComponent(() => import('@/components/charts/VChartLocal.vue'))

const el = ref(null)
defineExpose({ resize: () => el.value?.resize?.() })

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
	<VChartLocal
		ref="el"
		:option="option"
		:style="{ height: props.height, width: '100%' }"
		autoresize
	/>
</template>
