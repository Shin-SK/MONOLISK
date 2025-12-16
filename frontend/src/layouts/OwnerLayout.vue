<!-- /layouts/OwnerLayout.vue -->
<script setup>
import { computed, onMounted, ref, nextTick, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { api } from '@/api'
import dayjs from 'dayjs'
import { useNow } from '@vueuse/core'
import { useProfile } from '@/composables/useProfile'
import OwnerSidebar from '@/components/sidebar/OwnerSidebar.vue'
import Avatar from '@/components/Avatar.vue'
import { installAutoCloseOnRoute, openOffcanvas } from '@/utils/bsOffcanvas'
import { useBills } from '@/stores/useBills'
import { useTableAlerts } from '@/composables/useTableAlerts'

/* stores / router */
const router = useRouter()
const route  = useRoute()
const user   = useUser()
const { avatarURL } = useProfile() 

onMounted(() => {
  installAutoCloseOnRoute(router)
})

function openSidebar(){
  openOffcanvas('#ownerSidebar')
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

// ★ いまのページを"軽く"リフレッシュ（子コンポーネント再マウント）
async function onClickRefresh () {
  try {
    refreshing.value = true
    viewKey.value += 1     // ← これで <component :key="viewKey" /> が再マウント
    await nextTick()
  } finally {
    setTimeout(() => { refreshing.value = false }, SPIN_MS + 100)
  }
}

/* ───── テーブルアラート表示 ───── */
const billsStore = useBills()
const { getAlertState, urgentBills, urgentCount, cleanup: cleanupAlerts } = useTableAlerts(
  computed(() => billsStore.list)
)

const showAlertModal = ref(false)

function toggleAlertModal() {
  showAlertModal.value = !showAlertModal.value
}

function closeAlertModal() {
  showAlertModal.value = false
}

function handleAlertClick(bill) {
  closeAlertModal()
  router.push({ name: 'owner-bill-table', query: { billId: bill.id } })
}

onBeforeUnmount(() => {
  cleanupAlerts()
})
const isActiveName = (name) => route.name === name

/* logout もそのまま */
async function logout () {
  try { await api.post('dj-rest-auth/logout/') } catch {}
  user.clear()
  router.push('/login')
}
</script>

<template>
  <div class="base owner-layout d-block d-md-flex min-vh-100"
    style="z-index: 99;">

    <!-- ────────── MAIN ────────── -->
    <main class="main flex-fill container-fluid py-4">
      <div class="wrapper h-100 d-flex flex-column">
        <header class="header d-flex justify-content-between mb-1">
            <h2>{{ pageTitle }}</h2>
             <div class="position-relative">
              <button 
                class="btn btn-sm position-relative"
                @click="toggleAlertModal"
                :class="{ 'text-danger': urgentCount > 0 }"
              >
                <IconBell class="fs-5"/>
                <span 
                  v-if="urgentCount > 0"
                  class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger"
                  style="font-size: 0.65rem; padding: 0.35rem 0.5rem;"
                >
                  {{ urgentCount }}
                </span>
              </button>
            </div>
        </header>

        <!-- モーダル背景（暗い敷き） -->
        <Transition name="fade">
          <div 
            v-if="showAlertModal"
            class="modal-backdrop-dark"
            @click="closeAlertModal"
          ></div>
        </Transition>

        <!-- アラートモーダル（上からスライドイン） -->
        <Transition name="slide-down">
          <div 
            v-if="showAlertModal"
            class="alert-modal-sheet"
          >
            <!-- ハンドル -->
            <div class="modal-handle"></div>

            <!-- ヘッダー -->
            <div class="modal-header">
              <h5 class="m-0">通知</h5>
              <button 
                class="btn-close"
                @click="closeAlertModal"
              ></button>
            </div>

            <!-- アラート一覧 -->
            <div class="modal-body py-3">
              <div v-if="urgentBills.length > 0" class="alert-list">
                <div 
                  v-for="bill in urgentBills"
                  :key="bill.id"
                  class="alert-item"
                >
                  <router-link
                    :to="{ name: 'owner-bill-table', query: { billId: bill.id } }"
                    @click.prevent="handleAlertClick(bill)"
                  >
                      <div class="alert-item-header">
                        <div class="fw-bold text-danger">卓番: {{ bill.table?.number || bill.table || '—' }}</div>
                        <div class="alert-badge">{{ getAlertState(bill)?.message || '' }}</div>
                      </div>
                      <div class="alert-item-body">
                        <div class="small text-muted">{{ bill.customer_display_name || '顧客名未設定' }}</div>
                      </div>
                  </router-link>
                </div>
              </div>

              <!-- アラートなし -->
              <div v-else class="text-muted text-center py-5">
                <small>通知はありません</small>
              </div>
            </div>
          </div>
        </Transition>
        <div class="position-relative flex-fill">
          <router-view v-slot="{ Component }">
            <Suspense>
              <template #default>
                <component :is="Component" :key="viewKey" />
              </template>
            </Suspense>
          </router-view>
        </div>
      </div>
    </main>

    <!-- ────────── footer ────────── -->
    <div class="position-fixed bottom-0 w-100 d-flex align-items-center justify-content-between gap-3 bg-white p-2"
    style="z-index: 99;">
      <button 
        class="df-center flex-column"
        :class="route.name === 'owner-dashboard' && !route.query.tab ? 'text-dark' : 'text-secondary'"
        @click="$router.push({ name:'owner-dashboard', query: { tab: 'home' } })">
        <span>
          <IconHomeFilled v-if="route.name === 'owner-dashboard' && !route.query.tab" />
          <IconHome v-else />
        </span>
        <small>ホーム</small>
      </button>

      <button 
        class="df-center flex-column"
        :class="route.query.tab === 'bills' ? 'text-dark' : 'text-secondary'"
        @click="$router.push({ name:'owner-dashboard', query: { tab: 'bills' } })">
        <span>
          <IconLayoutListFilled v-if="route.query.tab === 'bills'" />
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
    </div>

    <OwnerSidebar />
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

/* ───── アラートモーダルのスタイル ───── */

/* 背景の暗い敷き（Fade） */
.modal-backdrop-dark {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1040;
}

/* モーダルシート本体 */
.alert-modal-sheet {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1050;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #f8f9fa 0%, #fff 100%);
  border-radius:0 0 16px 16px;
  max-height: 50vh;
  overflow-y: auto;
  box-shadow: 0 -2px 20px rgba(0, 0, 0, 0.1);
}

/* ハンドル（引っ張って閉じるイメージ） */
.modal-handle {
  width: 40px;
  height: 4px;
  background-color: #ccc;
  border-radius: 2px;
  align-self: center;
  margin-top: 12px;
  margin-bottom: 12px;
}

/* モーダルのヘッダー */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e9ecef;
  flex-shrink: 0;
}

.modal-header h5 {
  font-weight: 600;
  font-size: 1.1rem;
}

/* モーダルのボディ */
.modal-body {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
}

/* アラート項目 */
.alert-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-left: 4px solid #dc3545;
  background-color: #fff5f5;
  border-radius: 8px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.alert-item:hover {
  background-color: #ffe6e6;
  transform: translateX(4px);
}

.alert-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.alert-badge {
  display: inline-block;
  background-color: #dc3545;
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

.alert-item-body {
  padding-top: 4px;
}

/* Transition: スライドダウン */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-down-enter-from {
  transform: translateY(-100%);
  opacity: 0;
}

.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

/* 低モーション対応 */
@media (prefers-reduced-motion: reduce) {
  .alert-modal-sheet,
  .modal-backdrop-dark {
    transition: none;
  }

  .alert-item {
    transition: none;
  }
}
</style>