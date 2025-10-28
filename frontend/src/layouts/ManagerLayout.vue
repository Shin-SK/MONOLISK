<!-- /layouts/ManagerLayout.vue -->
<script setup>
import { computed, onMounted, ref, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'
import { useProfile } from '@/composables/useProfile'
import ManagerSidebar from '@/components/sidebar/ManagerSidebar.vue'
import Avatar from '@/components/Avatar.vue'
import { installAutoCloseOnRoute, openOffcanvas } from '@/utils/bsOffcanvas'

/* stores / router */
const router = useRouter()
const route  = useRoute()
const user   = useUser()
const { avatarURL } = useProfile() 

onMounted(() => {
  installAutoCloseOnRoute(router)
})

function openSidebar(){
  openOffcanvas('#managerSidebar')
}

const currentRole = computed(() => user.me?.current_role || null)
const isStaff     = computed(() => currentRole.value === 'staff')

/* ページタイトル・日付などはそのまま */
const pageTitle = computed(() => route.meta.title || 'Untitled')
const today     = computed(() =>
  dayjs(useNow({ interval: 60_000 }).value).format('YYYY.MM.DD (ddd)')
)

/* ★ リフレッシュ制御 */
const refreshing = ref(false)
const viewKey    = ref(0)
const SPIN_MS    = 2500 

async function refreshPage () {
  try {
    refreshing.value = true
    // 子コンポーネントを再マウントして各画面の onMounted/load を再実行
    viewKey.value += 1
    await nextTick()
  } finally {
    setTimeout(() => { refreshing.value = false }, SPIN_MS + 100) // 少し余裕を見て止める
  }
}

// ダッシュボタン押下時の挙動：
//  - すでにダッシュボードなら再読込
//  - 別ページなら遷移して、遷移完了で回転停止
async function onClickDashboard () {
  if (route.name === 'mng-dashboard') {
    await refreshPage()
  } else {
    refreshing.value = true
    try {
      await router.push({ name: 'mng-dashboard' })
    } finally {
      // ルート遷移後にちょい待って停止
      setTimeout(() => { refreshing.value = false }, SPIN_MS + 100)
    }
  }
}

/* ───── active 判定ヘルパ（name で判定） ───── */
const isActiveName = (name) => route.name === name

/* logout もそのまま */
async function logout () {
  try { await api.post('dj-rest-auth/logout/') } catch {}
  user.clear()
  router.push('/login')
}
</script>

<template>
  <div class="base managers d-block d-md-flex min-vh-100">
    <!-- ────────── footer ────────── -->
    <div class="sidebar d-flex align-items-center justify-content-md-start justify-content-between gap-3 gap-md-5">

      <!-- Manager サイドバー（idは #managerSidebar と一致） -->
      <button class="nav-link text-dark fs-md-2 fs-4" @click="openSidebar" aria-controls="managerSidebar" aria-label="メニューを開く">
        <Avatar :url="avatarURL" :size="40" class="rounded-circle" />
      </button>

      <RouterLink :to="{ name:'mng-bill-table' }" v-slot="{ href, navigate, isExactActive }">
        <a
          :href="href"
          @click="navigate"
          class="nav-link"
          :class="isExactActive ? 'bg-dark text-white' : 'bg-white text-dark'"
        >
          <IconPinned :size="24" />
        </a>
      </RouterLink>

      <RouterLink :to="{ name:'mng-bill-list' }" v-slot="{ href, navigate, isExactActive }">
        <a
          :href="href"
          @click="navigate"
          class="nav-link"
          :class="isExactActive ? 'bg-dark text-white' : 'bg-white text-dark'"
        >
          <IconList :size="24" />
        </a>
      </RouterLink>

      <RouterLink :to="{ name:'mng-bill-tl' }" v-slot="{ href, navigate, isExactActive }">
        <a
          :href="href"
          @click="navigate"
          class="nav-link"
          :class="isExactActive ? 'bg-dark text-white' : 'bg-white text-dark'"
        >
          <IconMenu3 :size="24" />
        </a>
      </RouterLink>

      <!-- ★ ダッシュボタン：色固定（反転なし） -->
      <button
        class="nav-link bg-white text-dark"
        @click="onClickDashboard"
        aria-label="ダッシュボードを再表示"
      >
        <IconRefresh :size="24" :class="{ spin: refreshing }" />
      </button>

      <ManagerSidebar />
    </div>

    <!-- ────────── MAIN ────────── -->
    <main class="main flex-fill container-fluid py-4">
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
                <!-- ★ viewKey で子を再マウント -->
                <component :is="Component" :key="viewKey" />
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
.fade-leave-active { transition: opacity .1s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }

/* ★回転アニメーション */
.spin {
  display: inline-block;
  animation: spinBackish 2.5s cubic-bezier(.175,.885,.32,1.275) 1 both;
  /*  ↑ Index と同じカーブ/中間角度、1回だけ再生＆最終フレーム保持 */
}
@keyframes spinBackish {
  0%   { transform: rotate(0deg); }
  60%  { transform: rotate(380deg); } /* オーバーシュート */
  100% { transform: rotate(360deg); } /* 少し戻して止まる */
}

/* 配慮: 低モーション設定のときはアニメ停止 */
@media (prefers-reduced-motion: reduce) {
  .spin { animation: none; }
}
</style>