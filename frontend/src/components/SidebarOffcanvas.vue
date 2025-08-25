<script setup>
import { computed }   from 'vue' 
import { useRoute }   from 'vue-router'
import { useRouter } from 'vue-router'
import { useUser }   from '@/stores/useUser'
import { api }       from '@/api'
import { closeSidebar } from '@/utils/offcanvas'
import { useAuth }   from '@/stores/useAuth'

const router = useRouter()
const route  = useRoute() 
const user   = useUser()
const auth   = useAuth()

/* ------------- 各セクションが「アクティブかどうか」を決める ------------- */
const shiftActive = computed(() =>
  ['/shifts', '/driver-shifts'].some(p => route.path.startsWith(p))
)

const settingsActive = computed(() =>
  ['/casts', '/drivers', '/customers'].some(p => route.path.startsWith(p))
)


async function logout () {
  await auth.logout()         // ストアの共通ロジックを呼ぶ
  router.push('/login')
  closeSidebar()              // off-canvas を閉じる
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
        <button
          class="btn-close"
          data-bs-dismiss="offcanvas"
        />
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between vh-100">
        <!-- -------- ナビ ---------- -->
        <nav class="nav flex-column h-100">
          <RouterLink
            class="nav-link"
            to="/"
            @click="closeSidebar"
          >
            ダッシュボード
          </RouterLink>
          <RouterLink
            class="nav-link"
            to="/bills/pl/daily"
            @click="closeSidebar"
          >
            PL/日次
          </RouterLink>
          <RouterLink
            class="nav-link"
            to="/bills/pl/monthly"
            @click="closeSidebar"
          >
            PL/月次
          </RouterLink>
          <RouterLink
            class="nav-link"
            to="/bills/pl/yearly"
            @click="closeSidebar"
          >
            PL/年次
          </RouterLink>
          <RouterLink
            class="nav-link"
            to="/bills/cast-shift"
            @click="closeSidebar"
          >
            キャストシフト
          </RouterLink>
          <RouterLink
            class="nav-link"
            to="/cast-sales"
            @click="closeSidebar"
          >
            キャスト売上
          </RouterLink>
          <RouterLink
            class="nav-link"
            to="/ranking"
            @click="closeSidebar"
          >
            ランキング
          </RouterLink>
          <RouterLink
            class="nav-link"
            to="/customers"
            @click="closeSidebar"
          >
            顧客情報
          </RouterLink>

          <RouterLink class="nav-link" to="/settings" @click="closeSidebar">設定</RouterLink>

          <div class="mt-auto">
            <a href="https://studio-color.jp/" class="d-flex text-black justify-content-between align-items-center" target="_black">
              <div class="wrap d-flex flex-column">
                <span style="font-size: 12px;">キャスト撮影やコンテンツ制作なら</span>  
                <span class="fw-bold fs-5">スタジオカラー</span>
              </div>
              <IconChevronRight />
            </a>

            <RouterLink
              class="nav-link mt-auto"
              to="/cast/mypage/1"
              @click="closeSidebar"
            >
              キャストマイページ（サンプルID=1）
            </RouterLink>
          </div>


        </nav>

        <!-- -------- フッタ ---------- -->
        <div class="mt-auto pt-3 border-top">
          <div class="d-flex align-items-center gap-2 mb-3">
            <Avatar :url="user.avatar_url" :size="40" class="rounded-circle"/>
            <span>{{ user.name }}</span>
          </div>
          <button
            class="btn btn-outline-danger w-100"
            @click.prevent="logout"
          >
            ログアウト
          </button>
        </div>
      </aside>
    </div>
  </teleport>
</template>


<style>
.rotate-90   { transform: rotate(90deg); transition: .2s; }
.rotate-0    { transform: rotate(0deg);  transition: .2s; }
</style>