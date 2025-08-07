<!-- components/Avatar.vue -->
<script setup>
import { computed } from 'vue'
import { avatarUrl } from '@/utils/cloudinary.js'

const props = defineProps({
  url : { type: String, default: '' },
  alt : { type: String, default: '' },
  size: { type: Number, default: 32 },
})

const sizePx = computed(() => `${props.size}px`)
const optimizedUrl = computed(() =>
  props.url ? avatarUrl(props.url, props.size, props.size) : ''
)
</script>

<template>
  <img
    v-if="optimizedUrl"
    :src="optimizedUrl"
    :alt="props.alt"
    :style="{ width: sizePx, height: sizePx }"
    class="object-fit-cover"
    loading="lazy"
  />
  <IconUserFilled
    v-else
    :style="{ fontSize: sizePx }"
  />
</template>
