<script setup>
import { ref, computed, watch } from 'vue'
import { useUser } from '@/stores/useUser'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { closeSidebar } from '@/utils/offcanvas'
import { useRoles } from '@/composables/useRoles'

const props = defineProps({
  // 再利用用：設置先に合わせてサイドバーIDを渡せる
  sidebarId: { type: String, default: 'ownerSidebar' },
})

const user = useUser()
const router = useRouter()
const { homePath } = useRoles()

const visible = computed(() => !!user.me?.is_superuser)
const current = ref(user.me?.current_role || 'manager')
const roles = ['cast','staff','manager','owner']

// meが更新されたらセレクトも追随
watch(() => user.me?.current_role, v => { if (v) current.value = v })

async function apply(){
  await api.post('accounts/debug/set-role/', { role: current.value })
  await user.fetchMe?.()

  // ① サイドバーを先に閉じる
  closeSidebar(props.sidebarId)

  // ② 役割で決まるホームへ
  const to = homePath()

  // ③ 同一路線なら no-op 防止のため強制リフレッシュ
  const nowPath = router.currentRoute.value.path
  if (nowPath === to) {
    router.replace({ path: to, query: { _r: Date.now().toString() } })
  } else {
    router.replace(to)
  }
}
</script>

<template>
  <div v-if="visible" class="d-flex align-items-center gap-2">
    <select v-model="current" class="form-select form-select-sm w-auto">
      <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
    </select>
    <button class="btn btn-sm btn-outline-secondary" @click="apply">Apply</button>
  </div>
</template>
