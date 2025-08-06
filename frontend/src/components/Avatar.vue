<!-- components/Avatar.vue -->
<template>
  <img
    v-if="url"
    :src="url"
    :alt="alt"
    :style="{ width: sizePx, height: sizePx }"
    class="rounded-circle object-fit-cover"
  >
  <IconUserFilled
    v-else
    :style="{ fontSize: sizePx }"
  />
</template>

<script setup>
const props = defineProps({
  url : String,
  alt : { type: String, default: '' },
  size: { type: Number, default: 32 },
})
const sizePx = `${props.size}px`
</script>
