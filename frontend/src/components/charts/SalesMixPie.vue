<script setup>
import { ref, computed, defineAsyncComponent } from 'vue'

const VChartLocal = defineAsyncComponent(() => import('@/components/charts/VChartLocal.vue'))

const el = ref(null)
defineExpose({ resize: () => el.value?.resize?.() })

const props = defineProps({
	items: { type: Array, required: true }, // [{name:'現金',value:...},{name:'カード',value:...}]
	height: { type: String, default: '300px' },
	title: { type: String, default: '' },
})
const option = computed(() => ({
	title: props.title ? { text: props.title, left: 'left', textStyle: { fontSize: 14 } } : undefined,
	tooltip: { trigger: 'item', valueFormatter: v => v.toLocaleString() },
	legend: { bottom: 0 },
	series: [{ type: 'pie', radius: ['40%', '70%'], avoidLabelOverlap: true, data: props.items }],
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
