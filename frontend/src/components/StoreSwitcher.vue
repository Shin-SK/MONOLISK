<template>
	<div v-if="visible" class="d-flex align-items-center gap-2">
		<select class="form-select form-select-sm" v-model="selected" @change="onChange">
			<option v-for="s in stores" :key="s.id" :value="String(s.id)">
				{{ s.name || s.display_name || ('#'+s.id) }}
			</option>
		</select>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { useRoles } from '@/composables/useRoles'
import { listMyStores, switchStore } from '@/api'

const router = useRouter()
const u = useUser()
const { homePath } = useRoles()

const stores   = ref([])
const selected = ref(localStorage.getItem('store_id') || '')

// superuser or owner のみ表示（storesが1件しかない場合も非表示にできる）
const isSuper  = computed(() => !!u.me?.is_superuser)
const isOwner  = computed(() => u.me?.current_role === 'owner')
const visible  = computed(() => (isSuper.value || isOwner.value) && stores.value.length > 0)

onMounted(async () => {
	try {
		stores.value = await listMyStores()
		// 現在のstore_idが所属外だったら u.fetchMe() で矯正されている想定
		if (!selected.value && stores.value[0]) {
			selected.value = String(stores.value[0].id)
		}
	} catch (e) {
		console.warn('[StoreSwitcher] failed to load stores', e)
	}
})

async function onChange(){
	try {
		// ヘッダ切替 + 現在role/capsを取り直し
		const me = await switchStore(selected.value)
		u.me = me                           // 反映
		u.setActiveStore(Number(selected.value)) // ピン留め更新（冪等）
		// 安全ホームへ
		const dest = homePath() || '/'
		router.replace(dest)
	} catch (e) {
		console.error('[StoreSwitcher] switch failed', e)
	}
}
</script>

<style scoped>
.form-label { min-width: 2.5rem; }
</style>
