<!-- frontend/src/components/BillModal.vue -->
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import BillModalPC from '@/components/BillModalPC.vue'
import BillModalSP from '@/components/BillModalSP.vue'

const props = defineProps({
  modelValue: Boolean,
  bill: Object,
  serviceRate: { type: Number, default: 0.3 },
  taxRate: { type: Number, default: 0.1 },
})
const emit = defineEmits(['update:modelValue','saved','updated','closed'])

const visible = computed({
  get: () => props.modelValue,
  set: v  => emit('update:modelValue', v)
})

const enableSP = true            // ★ SP切替を有効に
const mode = ref('pc')

function decide() {
  if (!enableSP) { mode.value = 'pc'; return }
  const isPC = window.matchMedia('(min-width: 768px)').matches
  mode.value = isPC ? 'pc' : 'sp'
}

// open時に“ロック”。既に開いていた場合にも対応
watch(visible, v => { if (v) decide() })
onMounted(() => { if (visible.value) decide() })
</script>

<template>
  <component
    :is="mode === 'pc' ? BillModalPC : BillModalSP"
    v-model="visible"
    :bill="bill"
    :service-rate="serviceRate"
    :tax-rate="taxRate"
    @saved="$emit('saved', $event)"
    @updated="$emit('updated', $event)"
    @closed="$emit('closed', $event)"
  />
</template>
