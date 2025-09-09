<!-- src/components/RefreshAvatar.vue -->
<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import Avatar from '@/components/Avatar.vue'

const props = defineProps({
	mode: { type: String, default: 'soft' }, // 'soft' | 'hard'
	label: { type: String, default: '更新' },
})

const user = useUser()
// /api/me の avatar_url を最優先、無ければ dj-rest-auth/user の avatar_url
const avatarURL = computed(() => user.me?.avatar_url || user.info?.avatar_url || '')

const router = useRouter()
const route  = useRoute()
async function refresh() {
	if (props.mode === 'hard') { window.location.reload(); return }
	const q = { ...route.query, _r: Date.now().toString() }
	await router.replace({ path: route.path, query: q })
}
</script>

<template>
	<button class="d-flex align-items-center gap-2 border-0 p-0" @click="refresh">
		<!-- ★ バインド（:url）+ 変数名は avatarURL -->
		<Avatar :url="avatarURL" :size="40" class="rounded-circle"/>
	</button>
</template>
