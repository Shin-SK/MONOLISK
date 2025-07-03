<!-- src/layouts/AdminLayout.vue -->
<script setup>
import { useRouter }  from 'vue-router'
import { useUser }    from '@/stores/useUser'
import { api }        from '@/api'
import { openSidebar } from '@/utils/offcanvas'

const router    = useRouter()
const userStore = useUser()

async function logout () {
  try { await api.post('dj-rest-auth/logout/') } catch {/* 無視 */}
  userStore.clear()
  router.push('/login')
}
</script>

<template>
  <div class="base admin d-flex min-vh-100">
    <header class="header">
      <button class="avatar-icon btn p-0 border-0 bg-transparent"
              @click="openSidebar">
        <img :src="userStore.avatar" class="rounded-circle" width="40" height="40" />
      </button>
    </header>

    <main class="flex-fill p-4">
      <router-view />
    </main>
    
  </div>
</template>
