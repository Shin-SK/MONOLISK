<!-- ManagerSidebar.vue -->
<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useUser }   from '@/stores/useUser'
import { useAuth }   from '@/stores/useAuth'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import StoreSwitcher from '@/components/StoreSwitcher.vue'
import { closeOffcanvas } from '@/utils/bsOffcanvas'

async function nav(to){
  await router.push(to)
  closeOffcanvas('#managerSidebar')
}

const router = useRouter()
const route  = useRoute()
const current = () => route.fullPath

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
    <div
      id="managerSidebar"
      class="offcanvas offcanvas-start"
      tabindex="-1"
      aria-labelledby="managerSidebarLabel">

      <div class="offcanvas-header">
        <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="閉じる"></button>
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between vh-100">
        <!-- -------- ナビ ---------- -->
        <nav class="nav flex-column">
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-dashboard'})">ダッシュボード</a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-bill-table'})">伝票</a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-pl-daily'})">PL/日次</a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-pl-monthly'})">PL/月次</a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-pl-yearly'})">PL/年次</a>

          <!-- ★ ステーション（Accordion 内も同様に go()） -->
          <div class="accordion accordion-flush my-2" id="accordionStations">
            <div class="accordion-item">
              <h2 class="accordion-header" id="headingStations">
                <button class="accordion-button collapsed px-2 text-muted bg-white" type="button"
                        data-bs-toggle="collapse" data-bs-target="#collapseStations"
                        aria-expanded="false" aria-controls="collapseStations">
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
                    <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav({name:'mng-kds-dishup'})">デシャップ</a>
                    <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav({name:'mng-kds-kitchen'})">キッチン</a>
                    <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav({name:'mng-kds-drinker'})">ドリンカー</a>
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
            <RouterLink class="nav-link bg-white"
              :to="{name: 'mng-profile'}"
              @click.prevent="nav({name:'mng-profile'})">
              <IconEdit :size="16" class="text-secondary" />
            </RouterLink>
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
