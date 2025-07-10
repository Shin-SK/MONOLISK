<!-- src/layouts/AdminLayout.vue -->
<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import { openSidebar } from '@/utils/offcanvas'
import AlertBell from '@/components/AlertBell.vue'

import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'      // ← 追加

/* ───── stores / router ───── */
const router    = useRouter()
const route     = useRoute()
const userStore = useUser()

/* ───── ① ページタイトル ───── */
const pageTitle = computed(() => route.meta.title || 'Untitled')

/* ───── ② 今日の日付 ───── */
const now       = useNow({ interval: 60_000 })          // 1分間隔で tick
const today     = computed(() => dayjs(now.value).format('YYYY.MM.DD (ddd)'))

/* ───── logout ───── */
async function logout () {
  try { await api.post('dj-rest-auth/logout/') } catch {}
  userStore.clear()
  router.push('/login')
}
</script>

<template>
  <div class="base admin d-flex min-vh-100">
    <div class="sidebar">
      <button class="avatar-icon btn p-0 border-0 bg-transparent"
              @click="openSidebar">
        <img :src="userStore.avatar" class="rounded-circle" width="40" height="40" />
      </button>
    </div>

    <main class="main flex-fill p-4">
      <div class="wrapper">
        <header class="header d-flex justify-content-between mb-5">
          <div class="area d-flex align-items-center gap-4">
            <h2>{{ pageTitle }}</h2>
            <span class="today text-muted">{{ today }}</span>
          </div><!-- area -->
          <div class="area">
            <AlertBell :alerts="cashAlerts" :dismissed="dismissed" class="me-3" />
          </div><!-- area -->
        </header>
        <router-view />
      </div>
    </main>
    
  </div>
</template>
