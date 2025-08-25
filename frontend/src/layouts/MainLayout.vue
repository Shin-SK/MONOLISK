<!--/layouts/MainLayout -->
<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import { openSidebar } from '@/utils/offcanvas'
import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'
import { useLoading } from '@/stores/useLoading'
import PageLoader from '@/components/PageLoader.vue'
const loading = useLoading()


/* stores / router */
const router = useRouter()
const route  = useRoute()
const user   = useUser()

/* ページタイトル・日付などはそのまま */
const pageTitle = computed(() => route.meta.title || 'Untitled')
const today     = computed(() => dayjs(useNow({interval:60_000}).value)
                              .format('YYYY.MM.DD (ddd)'))
const avatarSrc = computed(() => user.avatar || '/img/user-default.png')

/* ───── active 判定ヘルパ ───── */
const isActive = (p) => route.path === p

/* logout もそのまま */
async function logout () {
  try { await api.post('dj-rest-auth/logout/') } catch {}
  user.clear()
  router.push('/login')
}
</script>

<template>
  <div class="base admin d-block d-md-flex min-vh-100">

    <!-- ────────── SIDEBAR ────────── -->
    <div class="sidebar d-flex gap-5 align-items-center">
      <button class="avatar-icon btn p-0 border-0 bg-transparent"
              @click="openSidebar">
        <Avatar :url="user.avatar_url" :size="40" class="rounded-circle" />
      </button>

      <RouterLink
        class="nav-link"
        to="/dashboard"
        :class="isActive('/dashboard')
          ? 'bg-dark text-white'
          : 'bg-white text-dark'">
        <IconPinned :size="24"/>
      </RouterLink>

      <RouterLink
        class="nav-link"
        to="/dashboard/list"
        :class="isActive('/dashboard/list')
          ? 'bg-dark text-white'
          : 'bg-white text-dark'">
        <IconList :size="24"/>
      </RouterLink>
      <RouterLink
        class="nav-link"
        to="/dashboard/timeline"
        :class="isActive('/dashboard/timeline')
          ? 'bg-dark text-white'
          : 'bg-white text-dark'">
       <IconMenu3 :size="24"/>
      </RouterLink>

    </div>

    <!-- ────────── MAIN ────────── -->
    <main class="main flex-fill p-4">
      <div class="wrapper h-100 d-flex flex-column">
        <header class="header d-flex justify-content-between mb-1">
          <div class="area d-flex align-items-center gap-4">
            <h2>{{ pageTitle }}</h2>
            <span class="today text-muted">{{ today }}</span>
          </div>
        </header>
        <div class="position-relative flex-fill">
        <!-- ページ本体 -->
          <router-view v-slot="{ Component }">
            <Suspense>
              <!-- fallback は空にする ★ -->
              <template #default>
                <component :is="Component" />
              </template>
            </Suspense>
          </router-view>
          <PageLoader :active="useLoading().globalLoading" />

        </div>
      </div>
    </main>
  </div>
</template>


<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity .1s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>