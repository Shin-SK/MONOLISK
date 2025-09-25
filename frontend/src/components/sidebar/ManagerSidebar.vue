<!-- ManagerSidebar.vue -->
<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useUser }   from '@/stores/useUser'
import { useAuth }   from '@/stores/useAuth'
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
}
</script>

<template>
  <teleport to="body">
    <!-- <div
      id="managerSidebar"
      data-bs-scroll="false"
      class="offcanvas offcanvas-start"
      style="--bs-offcanvas-width: min(100vw,300px);"
      tabindex="-1"
    > -->
    <div
      id="managerSidebar"
      class="offcanvas offcanvas-start"
      tabindex="-1"
      aria-labelledby="managerSidebarLabel"
      data-bs-scroll="true"
      data-bs-backdrop="true"
    >
      <div class="offcanvas-header">
      <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="閉じる"></button>
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between vh-100">
        <!-- -------- ナビ ---------- -->
        <nav class="nav flex-column">

          <RouterLink class="nav-link bg-white" :to="{name:'mng-dashboard'}" data-bs-dismiss="offcanvas">ダッシュボード</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'mng-bill-table'}" data-bs-dismiss="offcanvas">伝票</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'mng-pl-daily'}" data-bs-dismiss="offcanvas">PL/日次</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'mng-pl-monthly'}" data-bs-dismiss="offcanvas">PL/月次</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'mng-pl-yearly'}" data-bs-dismiss="offcanvas">PL/年次</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'mng-cast-shift'}" data-bs-dismiss="offcanvas">キャストシフト</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'mng-cast-sales'}" data-bs-dismiss="offcanvas">キャスト売上</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'mng-ranking'}" data-bs-dismiss="offcanvas">ランキング</RouterLink>
          <RouterLink class="nav-link bg-white" :to="{name:'mng-customers'}" data-bs-dismiss="offcanvas">顧客情報</RouterLink>
          <RouterLink class="nav-link mt-2 bg-white" to="/settings" data-bs-dismiss="offcanvas">設定</RouterLink>
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
                    <!-- 旧: to="/kds/dishup" など（404の原因） -->
                    <RouterLink class="nav-link ps-3 ms-1 bg-white" :to="{ name:'mng-kds-dishup' }" data-bs-dismiss="offcanvas">デシャップ</RouterLink>
                    <RouterLink class="nav-link ps-3 ms-1 bg-white" :to="{ name:'mng-kds-kitchen' }"data-bs-dismiss="offcanvas">キッチン</RouterLink>
                    <RouterLink class="nav-link ps-3 ms-1 bg-white" :to="{ name:'mng-kds-drinker' }"data-bs-dismiss="offcanvas">ドリンカー</RouterLink>
                  </div>
                </div>
              </div>
            </div>
          </div>

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
        <div class="footer d-flex flex-column gap-2">
          <div class="d-flex justify-content-between align-items-center mb-3">

            <div class="d-flex align-items-center gap-2">
              <Avatar :url="avatarURL" :size="40" class="rounded-circle"/> 
              <span>{{ displayName }}</span>
            </div>
            <RouterLink class="nav-link bg-white" :to="{name: 'owner-profile'}"data-bs-dismiss="offcanvas"><IconEdit :size="16" class="text-secondary" /></RouterLink>
          </div>
          
          <button class="btn btn-outline-danger w-100" @click="logout">
            ログアウト
          </button>
          <StoreSwitcher class="mt-5" />
          <DevRoleSwitcher class="mt-1 mb-2"/>
        </div>
      </aside>
    </div>
  </teleport>
</template>
