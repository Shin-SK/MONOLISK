<!-- src/components/sidebar/CastSidebar.vue -->
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUser } from '@/stores/useUser'

const router = useRouter()
const userStore = useUser()
const rootPath = '/cast'

const displayName = computed(() =>
  userStore.me?.display_name || userStore.me?.username || 'Guest')

const avatar = computed(() =>
  userStore.avatar || userStore.me?.avatar || userStore.me?.profile_image || '')

const isCast = computed(() =>
  userStore.isCast || (userStore.me?.claims || []).includes('cast_order_self'))

async function logout() {
  try { await userStore.logout?.() } finally { router.push('/login') }//★ログアウトしますか？のalartを入れたい
}
</script>

<template>
  <div
    id="castSidebar"
    class="offcanvas offcanvas-start"
    style="--bs-offcanvas-width: 70vw;"
    tabindex="-1"
    aria-labelledby="castSidebarLabel"
  >
    <div class="offcanvas-header">
      <button type="button" class="btn-close text-reset" data-bs-dismiss="offcanvas" aria-label="Close"/>
    </div>

    <div class="offcanvas-body d-flex flex-column justify-content-between h-100 gap-3">
      <div class="wrap d-flex flex-column gap-2">
        <RouterLink
          class="btn w-100 d-flex justify-content-start"
          :to="{name: 'cast-mypage'}"
        >
        マイページ
        </RouterLink>
        <RouterLink class="btn w-100 d-flex" :to="`${rootPath}/profile`">
          プロフィール編集
        </RouterLink>

        <RouterLink
          v-if="isCast"
          class="btn w-100 d-flex"
          :to="`${rootPath}/sales`"
        >
          売上
        </RouterLink>
      </div>

      <div class="bottom d-flex flex-column gap-2">
        <div class="user d-flex gap-2 align-items-center">
          <img :src="avatar" class="rounded-circle" width="40" height="40" />
          <div class="fw-semibold small">{{ displayName }}</div>
        </div>
        <button class="btn btn-outline-danger w-100" @click="logout">
          ログアウト
        </button>
      </div>
    </div>
  </div>
</template>
