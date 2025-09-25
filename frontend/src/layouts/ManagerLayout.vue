<!-- /layouts/ManagerLayout.vue -->
<script setup>
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'
import { useProfile } from '@/composables/useProfile'
import ManagerSidebar from '@/components/sidebar/ManagerSidebar.vue'
import Avatar from '@/components/Avatar.vue'
import { installOffcanvasSingleton,closeAllOffcanvas } from '@/utils/offcanvas'
onMounted(() => {
  installOffcanvasSingleton()
  router.afterEach(() => { closeAllOffcanvas() })
})

/* stores / router */
const router = useRouter()
const route  = useRoute()
const user   = useUser()
const { avatarURL } = useProfile() 

const currentRole = computed(() => user.me?.current_role || null)
const isStaff     = computed(() => currentRole.value === 'staff')

/* ページタイトル・日付などはそのまま */
const pageTitle = computed(() => route.meta.title || 'Untitled')
const today     = computed(() =>
  dayjs(useNow({ interval: 60_000 }).value).format('YYYY.MM.DD (ddd)')
)

/* ★ ここを使う（このレイアウトでは useProfile を使っていない） */
const avatarSrc = computed(() => user.avatar || '/img/user-default.png')

/* ───── active 判定ヘルパ（name で判定） ───── */
const isActiveName = (name) => route.name === name

/* logout もそのまま */
async function logout () {
  try { await api.post('dj-rest-auth/logout/') } catch {}
  user.clear()
  router.push('/login')
}
</script>

<template>
  <div class="base managers d-block d-md-flex min-vh-100">
    <!-- ────────── footer ────────── -->
    <div class="sidebar d-flex align-items-center justify-content-md-start justify-content-between gap-3 gap-md-5">

      <RouterLink class="nav-link" :to="{ name: 'mng-dashboard' }">
        <Avatar :url="avatarURL" :size="40" class="rounded-circle" />
      </RouterLink>

      <RouterLink :to="{ name:'mng-bill-table' }" v-slot="{ href, navigate, isExactActive }">
        <a
          :href="href"
          @click="navigate"
          class="nav-link"
          :class="isExactActive ? 'bg-dark text-white' : 'bg-white text-dark'"
        >
          <IconPinned :size="24" />
        </a>
      </RouterLink>

      <RouterLink :to="{ name:'mng-bill-list' }" v-slot="{ href, navigate, isExactActive }">
        <a
          :href="href"
          @click="navigate"
          class="nav-link"
          :class="isExactActive ? 'bg-dark text-white' : 'bg-white text-dark'"
        >
          <IconList :size="24" />
        </a>
      </RouterLink>

      <RouterLink :to="{ name:'mng-bill-tl' }" v-slot="{ href, navigate, isExactActive }">
        <a
          :href="href"
          @click="navigate"
          class="nav-link"
          :class="isExactActive ? 'bg-dark text-white' : 'bg-white text-dark'"
        >
          <IconMenu3 :size="24" />
        </a>
      </RouterLink>


      <!-- Manager サイドバー（idは #managerSidebar と一致） -->
      <button
        class="nav-link text-dark fs-md-2 fs-4"
        data-bs-toggle="offcanvas"
        data-bs-target="#managerSidebar"
        aria-controls="managerSidebar"
      >
        <IconMenu2 :size="24"/>
      </button>

      <ManagerSidebar />
    </div>

    <!-- ────────── MAIN ────────── -->
    <main class="main flex-fill container-fluid py-4">
      <div class="wrapper h-100 d-flex flex-column">
        <header class="header d-flex justify-content-between mb-1">
          <div class="area d-flex align-items-center gap-4">
            <h2>{{ pageTitle }}</h2>
            <span class="today text-muted">{{ today }}</span>
          </div>
        </header>
        <div class="position-relative flex-fill">
          <router-view v-slot="{ Component }">
            <Suspense>
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
.fade-leave-active { transition: opacity .1s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>
