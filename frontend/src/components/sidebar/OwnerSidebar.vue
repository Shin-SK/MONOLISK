<!-- Sidebar.vue（差し替え） -->
<script setup>
import { computed } from 'vue'  
import { useRoute, useRouter } from 'vue-router'
import Avatar from '@/components/Avatar.vue'
import { useUser }   from '@/stores/useUser'
import { useAuth }   from '@/stores/useAuth'
import { closeSidebar } from '@/utils/offcanvas'
import { useProfile } from '@/composables/useProfile'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import StoreSwitcher from '@/components/StoreSwitcher.vue'

const router = useRouter()
const route  = useRoute()
const user   = useUser()
const auth   = useAuth()

const { displayName, avatarURL } = useProfile()

async function logout () {
  await auth.logout()
  router.push('/login')
  closeSidebar()
}
</script>

<template>
  <teleport to="body">
  <div
    id="ownerSidebar"
    class="offcanvas offcanvas-start flex-shrink-0 border-end bg-white"
    tabindex="-1"
    style="--bs-offcanvas-width: min(100vw,300px);">

      <div class="offcanvas-header bg-white">
        <button class="btn-close" data-bs-dismiss="offcanvas" />
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between vh-100">
        <!-- -------- ナビ ---------- -->
        <nav class="nav flex-column h-100">

          <RouterLink class="nav-link bg-white" to="/" @click="closeSidebar">ダッシュボード</RouterLink>
          <RouterLink class="nav-link bg-white" to="/pl/daily"      @click="closeSidebar">PL/日次</RouterLink>
          <RouterLink class="nav-link bg-white" to="/pl/monthly"    @click="closeSidebar">PL/月次</RouterLink>
          <RouterLink class="nav-link bg-white" to="/pl/yearly"     @click="closeSidebar">PL/年次</RouterLink>

          <RouterLink class="nav-link bg-white" to="/settings" @click="closeSidebar">設定</RouterLink>

          <div class="mt-auto">
            <a href="https://studio-color.jp/" class="d-flex text-black justify-content-between align-items-center" target="_black">
              <div class="wrap d-flex flex-column">
                <span style="font-size: 12px;">キャスト撮影やコンテンツ制作なら</span>
                <span class="fw-bold fs-5">スタジオカラー</span>
              </div>
            </a>
          </div>
        </nav>

        <!-- -------- フッタ ---------- -->
        <div class="mt-auto border-top">
          <div class="d-flex justify-content-between align-items-center mb-3">

            <div class="d-flex align-items-center gap-2">
              <Avatar :url="avatarURL" :size="40" class="rounded-circle"/> 
              <span>{{ displayName }}</span>
            </div>
            <RouterLink class="nav-link bg-white" :to="{name: 'owner-profile'}" @click="closeSidebar"><IconEdit :size="16" class="text-secondary" /></RouterLink>
          </div>

          <button class="btn btn-outline-danger w-100" @click.prevent="logout">ログアウト</button>
          <StoreSwitcher class="mt-5" />
          <DevRoleSwitcher class="mt-4 mb-2"/>
        </div>
      </aside>
    </div>
  </teleport>
</template>
