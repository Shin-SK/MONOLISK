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

// ★ いまのページを“軽く”リフレッシュ（子コンポーネント再マウント）
async function onClickRefresh () {
  try {
    refreshing.value = true
    viewKey.value += 1     // ← これで <component :key="viewKey" /> が再マウント
    await nextTick()
  } finally {
    setTimeout(() => { refreshing.value = false }, SPIN_MS + 100)
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
  <div class="base managers d-block d-md-flex min-vh-100"
    style="z-index: 99;">
    <!-- ────────── footer ────────── -->
    <div class="position-fixed bottom-0 w-100 d-flex align-items-center justify-content-between gap-3 bg-white p-2"
    style="z-index: 99;">
      <!-- <button>
         <Avatar :url="avatarURL" :size="40" class="rounded-circle" />
      </button> -->
      <button 
        class="df-center flex-column"
        :class="isActiveName('mng-dashboard') ? 'text-dark' : 'text-secondary'"
        @click="$router.push({ name:'mng-dashboard' })">
        <span>
          <IconHomeFilled v-if="isActiveName('mng-dashboard')" />
          <IconHome v-else />
        </span>
        <small>ホーム</small>
      </button>
      <button 
        class="df-center flex-column"
        :class="isActiveName('mng-bill-table') ? 'text-dark' : 'text-secondary'"
        @click="$router.push({ name:'mng-bill-table' })">
        <span>
          <IconPinnedFilled v-if="isActiveName('mng-bill-table')" />
          <IconPinned v-else />
        </span>
        <small>卓伝票</small>
      </button>
      <button 
        class="df-center flex-column"
        :class="isActiveName('mng-bill-list') ? 'text-dark' : 'text-secondary'"
        @click="$router.push({ name:'mng-bill-list' })">
        <span>
          <IconLayoutListFilled v-if="isActiveName('mng-bill-list')" />
          <IconLayoutList v-else />
        </span>
        <small>伝票一覧</small>
      </button>
      <button class="df-center flex-column text-secondary" @click="openSidebar" aria-controls="managerSidebar">
        <span>
          <IconList />
        </span>
        <small>設定</small>
      </button>

       <ManagerSidebar />
    </div>


    <!-- ────────── MAIN ────────── -->
    <main class="main flex-fill container-fluid py-4">
      <div class="wrapper h-100 d-flex flex-column">
        <header class="header d-flex justify-content-between mb-1">
            <h2>{{ pageTitle }}</h2>
            <span class="today text-muted">{{ today }}</span>
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