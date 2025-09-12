<!--/layouts/OwnerLayout -->
<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import { openSidebar } from '@/utils/offcanvas'
import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'
import OwnerSidebar from '@/components/sidebar/OwnerSidebar.vue'
import RefreshAvatar from '../components/RefreshAvatar.vue'

/* stores / router */
const router = useRouter()
const route  = useRoute()
const user   = useUser()

const currentRole = computed(() => user.me?.current_role || null)
const isStaff   = computed(() => currentRole.value === 'staff')


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
  <div class="base owner d-block d-md-flex min-vh-100">
    <!-- ────────── footer ────────── -->
    <div class="sidebar d-flex gap-5 align-items-center">

      <button>
        <RefreshAvatar />
      </button>

      <RouterLink
        class="nav-link"
        :to="{name:'owner-pl-daily'}"
        :class="isActive('/dashboard')
          ? 'bg-dark text-white'
          : 'text-dark'">
        <span class="monst">D</span>
      </RouterLink>

      <RouterLink
        class="nav-link"
        :to="{name:'owner-pl-monthly'}"
        :class="isActive('/dashboard/list')
          ? 'bg-dark text-white'
          : 'text-dark'">
        <span class="monst">M</span>
      </RouterLink>
      <RouterLink
        class="nav-link"
        :to="{name:'owner-pl-yearly'}"
        :class="isActive('/dashboard/timeline')
          ? 'bg-dark text-white'
          : 'text-dark'">
        <span class="monst">Y</span>
      </RouterLink>

      <button class="nav-link text-dark fs-md-2 fs-4" data-bs-toggle="offcanvas" data-bs-target="#ownerSidebar">
        <IconMenu2 :size="24"/>
      </button>
      <OwnerSidebar />

    </div>

    <!-- ────────── MAIN ────────── -->
    <main class="main flex-fill container py-4">
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