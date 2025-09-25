<!-- ManagerSidebar.vue -->
<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useUser }   from '@/stores/useUser'
import { useAuth }   from '@/stores/useAuth'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import StoreSwitcher from '@/components/StoreSwitcher.vue'
import { closeOffcanvas } from '@/utils/offcanvas'

async function nav(to){
  const r = router.resolve(to)
  await router.push(r)
  closeOffcanvas('#managerSidebar')   // ← ここだけでOK（BackdropはBootstrap任せ）
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
          <!-- ★ すべて go() で “遷移→閉じる” に統一 -->
          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-dashboard'}"
            @click.prevent="nav({name:'mng-bill-table'})">
            ダッシュボード
          </RouterLink>

          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-bill-table'}"
            @click.prevent="nav({name:'mng-bill-table'})">
            伝票
          </RouterLink>

          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-pl-daily'}"
            @click.prevent="nav({name:'mng-pl-daily'})">
            PL/日次
          </RouterLink>

          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-pl-monthly'}"
            @click.prevent="nav({name:'mng-pl-monthly'})">
            PL/月次
          </RouterLink>

          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-pl-yearly'}"
            @click.prevent="nav({name:'mng-pl-yearly'})">
            PL/年次
          </RouterLink>

          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-cast-shift'}"
            @click.prevent="nav({name:'mng-cast-shift'})">
            キャストシフト
          </RouterLink>

          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-cast-sales'}"
            @click.prevent="nav({name:'mng-cast-sales'})">
            キャスト売上
          </RouterLink>

          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-ranking'}"
            @click.prevent="go(router, {name:'mng-ranking'}, 'managerSidebar', current())">
            ランキング
          </RouterLink>

          <RouterLink class="nav-link bg-white"
            :to="{name:'mng-customers'}"
            @click.prevent="go(router, {name:'mng-customers'}, 'managerSidebar', current())">
            顧客情報
          </RouterLink>

          <RouterLink class="nav-link mt-2 bg-white"
            :to="{name:'settings'}"
            @click.prevent="go(router, {name:'mng-settings'}, 'managerSidebar', current())">
            設定
          </RouterLink>

          <!-- ★ ステーション（Accordion 内も同様に go()） -->
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
                    <RouterLink class="nav-link ps-3 ms-1 bg-white"
                      :to="{ name:'mng-kds-dishup' }"
                      @click.prevent="nav({name:'mng-kds-dishup'})">
                      デシャップ
                    </RouterLink>
                    <RouterLink class="nav-link ps-3 ms-1 bg-white"
                      :to="{ name:'mng-kds-kitchen' }"
                     @click.prevent="nav({name:'mng-kds-kitchen'})">
                      キッチン
                    </RouterLink>
                    <RouterLink class="nav-link ps-3 ms-1 bg-white"
                      :to="{ name:'mng-kds-drinker' }"
                      @click.prevent="nav({name:'mng-kds-drinker'})">
                      ドリンカー
                    </RouterLink>
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
