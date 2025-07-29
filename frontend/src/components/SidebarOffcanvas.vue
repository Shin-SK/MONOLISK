<script setup>
import { computed }   from 'vue' 
import { useRoute }   from 'vue-router'
import { useRouter } from 'vue-router'
import { useUser }   from '@/stores/useUser'
import { api }       from '@/api'
import { closeSidebar } from '@/utils/offcanvas'

const router = useRouter()
const route  = useRoute() 
const user   = useUser()

/* ------------- 各セクションが「アクティブかどうか」を決める ------------- */
const shiftActive = computed(() =>
  ['/shifts', '/driver-shifts'].some(p => route.path.startsWith(p))
)

const settingsActive = computed(() =>
  ['/casts', '/drivers', '/customers'].some(p => route.path.startsWith(p))
)


async function logout () {
  try { await api.post('dj-rest-auth/logout/') } catch {/* ignore */}
  user.clear()
  router.push('/login')
}
</script>

<template>
  <teleport to="body">
    <div id="appSidebar"
         class="offcanvas offcanvas-start"
         style="--bs-offcanvas-width: min(50vw,300px);" tabindex="-1">
      <div class="offcanvas-header">
        <button class="btn-close" data-bs-dismiss="offcanvas"></button>
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between vh-100">
        <!-- -------- ナビ ---------- -->
        <nav class="nav flex-column h-100">
          <RouterLink class="nav-link" to="/" @click="closeSidebar">ダッシュボード</RouterLink>
          <!-- <RouterLink class="nav-link" to="/bills"  @click="closeSidebar">伝票一覧</RouterLink> -->
          <RouterLink class="nav-link" to="/bills/pl/daily" @click="closeSidebar">PL/日次</RouterLink>
          <RouterLink class="nav-link" to="/bills/pl/monthly" @click="closeSidebar">PL/月次</RouterLink>
          <RouterLink class="nav-link" to="/bills/pl/yearly" @click="closeSidebar">PL/年次</RouterLink>
          <RouterLink class="nav-link" to="/bills/cast-shift" @click="closeSidebar">キャストシフト</RouterLink>
          <RouterLink class="nav-link" to="/cast-sales" @click="closeSidebar">キャスト売上</RouterLink>

          <!-- <RouterLink class="nav-link" to="/expense/form" @click="closeSidebar">経費申請</RouterLink> -->
          <button
            class="nav-link d-flex justify-content-between align-items-center fw-semibold"
            data-bs-toggle="collapse"
            data-bs-target="#shiftCollapse"
            :class="{ collapsed: !shiftActive }" 
            type="button">
            設定
           <i class="bi bi-chevron-right"></i>
          </button>

          <div
            id="shiftCollapse"
            class="collapse ps-3"
            :class="{ show: shiftActive }">
            <RouterLink class="nav-link" to="/casts" @click="closeSidebar">キャスト情報</RouterLink>
          </div>

          <RouterLink class="nav-link mt-auto" to="/cast/mypage/1" @click="closeSidebar">キャストマイページ（サンプルID=1）</RouterLink>
        </nav>

        <!-- -------- フッタ ---------- -->
        <div class="mt-auto pt-3 border-top">
          <div class="d-flex align-items-center gap-2 mb-3">
            <img :src="user.avatar" class="rounded-circle" width="32" height="32" />
            <span>{{ user.name }}</span>
          </div>
          <button class="btn btn-outline-danger w-100" @click.prevent="logout">ログアウト</button>
        </div>
      </aside>
    </div>
  </teleport>
</template>


<style>
.rotate-90   { transform: rotate(90deg); transition: .2s; }
.rotate-0    { transform: rotate(0deg);  transition: .2s; }
</style>