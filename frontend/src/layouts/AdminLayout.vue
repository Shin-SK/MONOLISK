<!-- src/layouts/AdminLayout.vue -->
<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import { openSidebar } from '@/utils/offcanvas'
import AlertBell from '@/components/AlertBell.vue'

import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'

/* ───── stores / router ───── */
const router    = useRouter()
const route     = useRoute()
const userStore = useUser()

/* ───── ① ページタイトル ───── */
const pageTitle = computed(() => route.meta.title || 'Untitled')

/* ───── ② 今日の日付 ───── */
const now       = useNow({ interval: 60_000 })
const today     = computed(() => dayjs(now.value).format('YYYY.MM.DD (ddd)'))

/* ───── ③ アバター画像 ───── */
const avatarSrc = computed(() => {
  /* userStore.avatar（＝ログイン API で返した avatar_url）が
     null/空文字/undefined ならデフォルト png を返す */
  const url = userStore.avatar
  return url ? url : '/img/user-default.png'
})

/* ───── logout ───── */
async function logout () {
  try { await api.post('dj-rest-auth/logout/') } catch {}
  userStore.clear()
  router.push('/login')
}
</script>

<template>
  <div class="base admin d-flex min-vh-100">
    <!-- ────────── SIDEBAR ────────── -->
    <div class="sidebar">
      <button class="avatar-icon btn p-0 border-0 bg-transparent"
              @click="openSidebar">
        <!-- ↓ フォールバック込みの avatarSrc を使用 -->
        <img :src="avatarSrc" class="rounded-circle" width="40" height="40" />
      </button>
    </div>

    <!-- ────────── MAIN ────────── -->
    <main class="main flex-fill p-4">
      <div class="wrapper">
        <header class="header d-flex justify-content-between mb-5">
          <div class="area d-flex align-items-center gap-4">
            <h2>{{ pageTitle }}</h2>
            <span class="today text-muted">{{ today }}</span>
          </div>

          <!-- もし cashAlerts / dismissed が未定義なら
               ↓ の行をコメントアウト or 代替実装してください -->
          <!-- <AlertBell :alerts="cashAlerts" :dismissed="dismissed" class="me-3" /> -->
        </header>

        <!-- ページ本体 -->
        <router-view />
      </div>
    </main>
  </div>
</template>
