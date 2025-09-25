<script setup>
import { useRoute, useRouter } from 'vue-router'
import Avatar from '@/components/Avatar.vue'
import { useAuth } from '@/stores/useAuth'
import { useProfile } from '@/composables/useProfile'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import StoreSwitcher from '@/components/StoreSwitcher.vue'
import { closeOffcanvas } from '@/utils/offcanvas'

const router = useRouter()
const route  = useRoute()
const { displayName, avatarURL } = useProfile()

// Manager と同じパターン：遷移 → すぐ JS で閉じる（data-bs-dismissは使わない）
function nav(to){
  const dst = router.resolve(to)
  if (route.fullPath !== dst.fullPath) {
    router.push(dst)
  }
  closeOffcanvas('#ownerSidebar')
}

const auth = useAuth()
async function logout () {
  await auth.logout()
  closeOffcanvas('#ownerSidebar')
  router.push('/login')
}
</script>

<template>
  <teleport to="body">
    <div
      id="ownerSidebar"
      class="offcanvas offcanvas-start flex-shrink-0 border-end bg-white"
      tabindex="-1"
      style="--bs-offcanvas-width: min(100vw,300px);"
      aria-labelledby="ownerSidebarLabel"
      data-bs-scroll="true"
      data-bs-backdrop="true"
    >
      <div class="offcanvas-header bg-white">
        <button class="btn-close" data-bs-dismiss="offcanvas" aria-label="閉じる" />
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between vh-100">
        <nav class="nav flex-column h-100">
          <RouterLink class="nav-link bg-white" :to="{name:'owner-dashboard'}" @click.prevent="nav({name:'owner-dashboard'})">ダッシュボード</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'owner-pl-daily'}"   @click.prevent="nav({name:'owner-pl-daily'})">PL/日次</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'owner-pl-monthly'}" @click.prevent="nav({name:'owner-pl-monthly'})">PL/月次</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'owner-pl-yearly'}"  @click.prevent="nav({name:'owner-pl-yearly'})">PL/年次</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'settings'}"         @click.prevent="nav({name:'settings'})">設定</RouterLink>

          <div class="mt-auto">
            <a href="https://studio-color.jp/" class="d-flex text-black justify-content-between align-items-center" target="_blank" rel="noopener">
              <div class="wrap d-flex flex-column">
                <span style="font-size: 12px;">キャスト撮影やコンテンツ制作なら</span>
                <span class="fw-bold fs-5">スタジオカラー</span>
              </div>
            </a>
          </div>
        </nav>

        <div class="mt-auto border-top pt-3">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <div class="d-flex align-items-center gap-2">
              <Avatar :url="avatarURL" :size="40" class="rounded-circle"/>
              <span>{{ displayName }}</span>
            </div>
            <RouterLink class="nav-link bg-white" :to="{name:'owner-profile'}" @click.prevent="nav({name:'owner-profile'})">
              <IconEdit :size="16" class="text-secondary" />
            </RouterLink>
          </div>

          <button class="btn btn-outline-danger w-100" @click.prevent="logout">ログアウト</button>
          <StoreSwitcher class="mt-5" />
          <DevRoleSwitcher class="mt-4 mb-2"/>
        </div>
      </aside>
    </div>
  </teleport>
</template>
