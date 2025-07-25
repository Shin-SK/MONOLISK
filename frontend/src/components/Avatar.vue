<!-- components/Avatar.vue -->
<template>
  <img
    v-if="url"
    :src="url"
    :alt="alt"
    :style="{ width: sizePx, height: sizePx }"
    class="rounded-circle object-fit-cover"
  >
  <i v-else class="bi bi-person-circle" :style="{ fontSize: sizePx }"></i>
</template>

<script setup>
const props = defineProps({
  url : String,
  alt : { type: String, default: '' },
  size: { type: Number, default: 32 },
})
const sizePx = `${props.size}px`
</script>
