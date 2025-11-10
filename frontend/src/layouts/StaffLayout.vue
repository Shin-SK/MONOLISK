<!-- /layouts/StaffLayout.vue -->
<script setup>
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'
import StaffSidebar from '@/components/sidebar/StaffSidebar.vue'
import { useProfile } from '@/composables/useProfile'
import RefreshAvatar from '@/components/RefreshAvatar.vue'
import { installAutoCloseOnRoute, openOffcanvas } from '@/utils/bsOffcanvas'

const router = useRouter()
const route  = useRoute()
const user   = useUser()
const { avatarURL, displayName } = useProfile()


onMounted(() => {
  installAutoCloseOnRoute(router)
})

function openSidebar(){
  openOffcanvas('#staffSidebar')
}


const pageTitle = computed(() => route.meta.title || 'Untitled')
const today     = computed(() =>
  dayjs(useNow({ interval: 60_000 }).value).format('YYYY.MM.DD (ddd)')
)

const isActive = (p) => route.path === p

const isActiveName = (name) => route.name === name  // 追加（name用）

</script>

<template>
  <div class="base admin d-block d-md-flex min-vh-100">
    <!-- ────────── SIDEBAR トリガー ────────── -->
    <div class="sidebar d-flex align-items-center justify-content-md-start justify-content-between gap-3 gap-md-5">
      <RefreshAvatar />

      <RouterLink class="nav-link"
                  :to="{ name: 'staff-dashboard' }"
                  :class="isActiveName('staff-dashboard') ? 'bg-dark text-white' : 'bg-white text-dark'">
        <IconPinned :size="24" />
      </RouterLink>

      <RouterLink class="nav-link"
                  :to="{ name: 'staff-dashboard-list' }"
                  :class="isActiveName('staff-dashboard-list') ? 'bg-dark text-white' : 'bg-white text-dark'">
        <IconList :size="24" />
      </RouterLink>

      <RouterLink class="nav-link"
                  :to="{ name: 'staff-dashboard-timeline' }"
                  :class="isActiveName('staff-dashboard-timeline') ? 'bg-dark text-white' : 'bg-white text-dark'">
        <IconMenu3 :size="24" />
      </RouterLink>

      
      <button class="nav-link text-dark fs-md-2 fs-4" @click="openSidebar" aria-controls="staffSidebar" aria-label="メニューを開く">
        <IconMenu2 :size="24" />
      </button>

      <StaffSidebar />
    </div>

    <!-- ────────── MAIN ────────── -->
    <main class="main flex-fill container-fluid">
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
                <component :is="Component" :key="$route.fullPath" />
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