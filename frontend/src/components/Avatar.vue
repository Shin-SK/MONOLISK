<!-- src/components/Avatar.vue -->
<script setup>
import { computed } from 'vue'
import { avatarUrl, avatarSrcset } from '@/utils/cloudinary.js'

const props = defineProps({
	url : { type: String, default: '' },
	alt : { type: String, default: '' },
	size: { type: Number, default: 40 },
})

const sizePx   = computed(() => `${props.size}px`)
const dpr      = Math.min(Math.round(window.devicePixelRatio || 1), 3)
const optimizedUrl = computed(() =>
	props.url ? avatarUrl(props.url, props.size * dpr, props.size * dpr) : ''
)
const srcset   = computed(() =>
	props.url ? avatarSrcset(props.url, props.size) : ''
)
// ★ 表示サイズに合わせて動的に
const sizesAttr = computed(() => `(max-width: 600px) ${props.size}px, ${props.size}px`)
</script>

<template>
	<img
		v-if="optimizedUrl"
		:src="optimizedUrl"
		:srcset="srcset"
		:sizes="sizesAttr"
		:alt="props.alt"
		:style="{ width: sizePx, height: sizePx }"
		class="object-fit-cover rounded-circle"
		loading="lazy"
		decoding="async"
	/>
	<IconUserFilled v-else :style="{ fontSize: sizePx }" />
</template>
