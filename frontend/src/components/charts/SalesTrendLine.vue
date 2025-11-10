<script setup>
import { ref, computed, defineAsyncComponent } from 'vue'

const VChartLocal = defineAsyncComponent(() => import('@/components/charts/VChartLocal.vue'))

const el = ref(null)
defineExpose({ resize: () => el.value?.resize?.() })

const props = defineProps({
	labels: Array,
	values: Array,
	height: { type: String, default: '320px' },
})

const option = computed(() => ({
	tooltip: { trigger: 'axis' },
	grid: { left: 40, right: 16, top: 24, bottom: 32 },
	xAxis: { type: 'category', data: props.labels },
	yAxis: { type: 'value' },
	series: [{ type: 'line', smooth: true, data: props.values, areaStyle: {} }],
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
