<!--/layouts/MainLayout -->
<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import { openSidebar } from '@/utils/offcanvas'
import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'
import StaffSidebar from '@/components/sidebar/StaffSidebar.vue'
import { useProfile } from '@/composables/useProfile'
import RefreshAvatar from '@/components/RefreshAvatar.vue'


/* stores / router */
const router = useRouter()
const route  = useRoute()
const user   = useUser()
const { avatarURL, displayName } = useProfile() 

const currentRole = computed(() => user.me?.current_role || null)
const isStaff   = computed(() => currentRole.value === 'staff')


/* ページタイトル・日付などはそのまま */
const pageTitle = computed(() => route.meta.title || 'Untitled')
const today     = computed(() => dayjs(useNow({interval:60_000}).value)
                              .format('YYYY.MM.DD (ddd)'))

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
      <button>
        <RefreshAvatar />
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

      <!-- staffなら #staffSidebar を開く -->
      <button v-if="isStaff"
        class="nav-link bg-white rounded-cirle"
        data-bs-toggle="offcanvas" data-bs-target="#staffSidebar" aria-controls="staffSidebar">
        <IconMenu2 :size="24"/>
      </button>

      <!-- それ以外は従来の openSidebar -->
      <button v-else class="nav-link" @click="openSidebar">
       <IconMenu2 :size="24"/>
      </button>
      
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
                <component :is="Component" :key="$route.fullPath" />
              </template>
            </Suspense>
          </router-view>
          <StaffSidebar v-if="isStaff" />
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