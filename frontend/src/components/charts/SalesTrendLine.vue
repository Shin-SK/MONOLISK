<!-- src/components/charts/SalesTrendLine.vue -->
<script setup>
import { ref, computed } from 'vue'
const el = ref(null)
defineExpose({ resize: () => el.value?.resize?.() })
const props = defineProps({ labels:Array, values:Array, height:{type:String,default:'320px'} })
const option = computed(() => ({
  tooltip:{ trigger:'axis' }, grid:{ left:40,right:16,top:24,bottom:32 },
  xAxis:{ type:'category', data:props.labels }, yAxis:{ type:'value' },
  series:[{ type:'line', smooth:true, data:props.values, areaStyle:{} }],
}))
</script>

<template>
  <VChart ref="el" :option="option" :style="{ height, width:'100%' }" autoresize />
</template>
