<!-- src/components/DevRoleSwitcher.vue -->
<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useUser } from '@/stores/useUser'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { closeSidebar } from '@/utils/offcanvas'
import { useRoles } from '@/composables/useRoles'

const props = defineProps({
	sidebarId: { type: String, default: 'ownerSidebar' },
})

const user = useUser()
const router = useRouter()
const { homePath } = useRoles()

// superuser or owner だけ表示
const visible = computed(() => !!user.me?.is_superuser || user.me?.current_role === 'owner')

const roles   = ['cast','staff','manager','owner']
const current = ref(user.me?.current_role || 'manager')
watch(() => user.me?.current_role, v => { if (v) current.value = v })

const applying = ref(false)

async function apply(){
	try {
		applying.value = true
		// ★ ここが修正点：role → current.value
		await api.get('accounts/debug/set-role/', { params: { role: current.value } })
		await user.fetchMe()   // ロール/権限を即反映

		// サイドバーを閉じてから安全ホームへ
		closeSidebar(props.sidebarId)
		await nextTick()

		const dest = homePath() || '/'
		const now  = router.currentRoute.value.path
		if (now === dest) {
			await router.replace({ path: dest, query: { _r: Date.now().toString() } })
		} else {
			await router.replace(dest)
		}
	} finally {
		applying.value = false
	}
}
</script>

<template>
  <div v-if="visible" class="row">
    <div class="col-8">
      <select v-model="current" class="form-select w-100">
        <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
      </select>
    </div>
    <div class="col-4">
      <button class="btn btn-outline-secondary w-100" :disabled="applying" @click="apply">
        更新
      </button>
    </div>
  </div>
</template>
