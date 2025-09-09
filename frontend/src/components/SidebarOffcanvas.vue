<!-- Sidebar.vue（差し替え） -->
<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useUser }   from '@/stores/useUser'
import { useAuth }   from '@/stores/useAuth'
import { closeSidebar } from '@/utils/offcanvas'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import StoreSwitcher from '@/components/StoreSwitcher.vue'

const router = useRouter()
const route  = useRoute()
const user   = useUser()
const auth   = useAuth()

const { avatarURL, displayName } = useProfile() 

async function logout () {
  await auth.logout()
  router.push('/login')
  closeSidebar()
}
</script>

<template>
  <teleport to="body">
    <div
      id="appSidebar"
      class="offcanvas offcanvas-start"
      style="--bs-offcanvas-width: min(100vw,300px);"
      tabindex="-1"
    >
      <div class="offcanvas-header">
        <button class="btn-close" data-bs-dismiss="offcanvas" />
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between vh-100">
        <!-- -------- ナビ ---------- -->
        <nav class="nav flex-column h-100">

          <RouterLink class="nav-link bg-white" to="/"                    @click="closeSidebar">ダッシュボード</RouterLink>
          <RouterLink class="nav-link bg-white" to="/pl/daily"      @click="closeSidebar">PL/日次</RouterLink>
          <RouterLink class="nav-link bg-white" to="/pl/monthly"    @click="closeSidebar">PL/月次</RouterLink>
          <RouterLink class="nav-link bg-white" to="/pl/yearly"     @click="closeSidebar">PL/年次</RouterLink>
          <RouterLink class="nav-link bg-white" to="/cast-shift"    @click="closeSidebar">キャストシフト</RouterLink>
          <RouterLink class="nav-link bg-white" to="/cast-sales"          @click="closeSidebar">キャスト売上</RouterLink>
          <RouterLink class="nav-link bg-white" to="/ranking"             @click="closeSidebar">ランキング</RouterLink>
          <RouterLink class="nav-link bg-white" to="/customers"           @click="closeSidebar">顧客情報</RouterLink>

          <!-- ★ ステーション（Bootstrap Accordion/Collapse） -->
          <div class="accordion accordion-flush my-2" id="accordionStations">
            <div class="accordion-item">
              <h2 class="accordion-header" id="headingStations">
                <button
                  class="accordion-button collapsed px-2 text-muted bg-white"
                  type="button"
                  data-bs-toggle="collapse"
                  data-bs-target="#collapseStations"
                  aria-expanded="false"
                  aria-controls="collapseStations"
                >
                  ステーション
                </button>
              </h2>
              <div
                id="collapseStations"
                class="accordion-collapse collapse"
                aria-labelledby="headingStations"
                data-bs-parent="#accordionStations"
              >
                <div class="accordion-body py-2 bg-white">
                  <div class="d-flex flex-column">
                    <RouterLink class="nav-link ps-3 ms-1 bg-white" to="/kds/dishup"  @click="closeSidebar">デシャップ</RouterLink>
                    <RouterLink class="nav-link ps-3 ms-1 bg-white" to="/kds/kitchen" @click="closeSidebar">キッチン</RouterLink>
                    <RouterLink class="nav-link ps-3 ms-1 bg-white" to="/kds/drinker" @click="closeSidebar">ドリンカー</RouterLink>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <RouterLink class="nav-link mt-2 bg-white" to="/settings" @click="closeSidebar">設定</RouterLink>

          <div class="mt-auto">
            <a href="https://studio-color.jp/" class="d-flex text-black justify-content-between align-items-center" target="_black">
              <div class="wrap d-flex flex-column">
                <span style="font-size: 12px;">キャスト撮影やコンテンツ制作なら</span>
                <span class="fw-bold fs-5">スタジオカラー</span>
              </div>
            </a>
            <RouterLink class="nav-link mt-3" to="/cast/mypage/1" @click="closeSidebar">
              キャストマイページ（サンプルID=1）
            </RouterLink>
          </div>
        </nav>

        <!-- -------- フッタ ---------- -->
        <div class="footer d-flex flex-column gap-2">
          <div class="d-flex justify-content-between align-items-center mb-3">

            <div class="d-flex align-items-center gap-2">
              <Avatar :url="avatarURL" :size="40" class="rounded-circle"/> 
              <span>{{ displayName }}</span>
            </div>
            <RouterLink class="nav-link bg-white" :to="{name: 'owner-profile'}" @click="closeSidebar"><IconEdit :size="16" class="text-secondary" /></RouterLink>
          </div>
          
          <button class="btn btn-outline-danger w-100" @click="logout">
            ログアウト
          </button>
          <StoreSwitcher class="mt-5" />
          <DevRoleSwitcher class="mt-4 mb-2"/>
        </div>
      </aside>
    </div>
  </teleport>
</template>
