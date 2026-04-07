<!-- ManagerSidebar.vue -->
<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUser }   from '@/stores/useUser'
import { useAuth }   from '@/stores/useAuth'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import StoreSwitcher from '@/components/StoreSwitcher.vue'
import { closeOffcanvas } from '@/utils/bsOffcanvas'
import { MANUALS } from '@/plugins/manuals'
import { openManual } from '@/utils/manuals'
import { APP_VERSION, GIT_SHA, BUILD_AT } from '@/version.gen.js'


async function nav(to){
  await router.push(to)
  closeOffcanvas('#managerSidebar')
}

const router = useRouter()
const route  = useRoute()
const current = () => route.fullPath

function openManualLink(p){
  openManual(p, router)
  closeOffcanvas('#managerSidebar')
}


const user   = useUser()
const auth   = useAuth()
const { avatarURL, displayName } = useProfile()

async function logout () {
  await auth.logout()
  router.push('/login')
}

// PC は常時表示の固定サイドバー、SP は offcanvas
const isPC = ref(false)
let mql = null
function syncIsPC(){ isPC.value = window.matchMedia('(min-width: 768px)').matches }
onMounted(() => {
  syncIsPC()
  mql = window.matchMedia('(min-width: 768px)')
  mql.addEventListener?.('change', syncIsPC)
})
onBeforeUnmount(() => { mql?.removeEventListener?.('change', syncIsPC) })
</script>

<template>
  <teleport to="body" :disabled="isPC">
    <div
      id="managerSidebar"
      :class="isPC ? 'manager-sidebar-pc' : 'offcanvas offcanvas-start'"
      tabindex="-1"
      aria-labelledby="managerSidebarLabel">

      <div class="offcanvas-header" v-if="!isPC">
        <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="閉じる"></button>
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between">
        <!-- -------- ナビ ---------- -->
        <nav class="nav flex-column">

          <div class="d-flex flex-column mb-3 pb-3 border-bottom gap-3">
            <!-- ダッシュボード -->
            <a class="nav-link bg-white d-flex align-items-center gap-1 fs-5" href="#" @click.prevent="nav({name:'mng-dashboard'})">
              <IconHome /><span class="lh-1">ホーム</span>
            </a>
            <!-- 卓伝票（PCではフッター廃止のためここに） -->
            <a class="nav-link bg-white d-flex align-items-center gap-1 fs-5" href="#" @click.prevent="nav({name:'mng-bill-table'})">
              <IconPinned /><span class="lh-1">卓伝票</span>
            </a>
            <!-- 伝票  -->
            <a class="nav-link bg-white d-flex align-items-center gap-1 fs-5" href="#" @click.prevent="nav({name:'mng-bills'})">
              <IconReceiptYen /><span class="lh-1">伝票一覧</span>
            </a>
            <!-- PL -->
            <a class="nav-link bg-white d-flex align-items-center gap-1 fs-5" href="#" @click.prevent="nav({name:'mng-pl'})">
              <IconChartHistogram /><span class="lh-1">収支分析</span>
            </a>
          </div>



          <!-- キャスト関連 -->
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-cast-shift'})">
            出退勤
          </a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-cast-shift-calendar'})">
            シフト一覧
          </a>
          <a class="nav-link bg-white d-none" href="#" @click.prevent="nav({name:'mng-cast-sales'})">
            キャスト売上（自動）
          </a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-cast-manual-subtotal'})">
            キャスト売上
          </a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-ranking'})">
            ランキング
          </a>

          <!-- 顧客 -->
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-customers'})">
            顧客情報
          </a>

          <!-- 給与（一時非表示） -->
          <a class="nav-link bg-white d-none" href="#" @click.prevent="nav({name:'Payroll'})">
            給与計算
          </a>
          <a class="nav-link bg-white d-none" href="#" @click.prevent="nav({name:'PayrollRuns'})">
            給与締め・出力
          </a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-excel-export'})">
            エクセル出力
          </a>

          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-profile'})">
            アカウント設定
          </a>

          <!-- 設定（ManagerLayout配下の /settings） -->
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'settings'})">
            設定
          </a>

          <a class="nav-link bg-white" href="#" @click.prevent="nav('/contact')">
            お問い合わせ
          </a>

          <!-- 操作マニュアル（一時非表示） -->
          <a class="nav-link bg-white d-none" href="#" @click.prevent="nav({name:'mng-manual'})">
            操作マニュアル
          </a>


            <!-- Manual アコーディオン jsとcomponentsから吐き出す -->
          <div class="accordion accordion-flush my-2 d-none" id="accordionManual">
            <div class="accordion-item">
              <h2 class="accordion-header" id="headingManual">
                <button
                  class="accordion-button collapsed px-2 text-muted bg-white"
                  type="button"
                  data-bs-toggle="collapse"
                  data-bs-target="#collapseManual"
                  aria-expanded="false"
                  aria-controls="collapseManual">
                  マニュアル
                </button>
              </h2>
              <div
                id="collapseManual"
                class="accordion-collapse collapse"
                aria-labelledby="headingManual"
                data-bs-parent="#accordionManual">
                <div class="accordion-body py-2 bg-white">
                  <div class="d-flex flex-column">
                    <!-- ★ 一覧をループ -->
                    <a
                      v-for="m in MANUALS"
                      :key="m.path"
                      class="nav-link ps-3 ms-1 bg-white"
                      :href="m.path"
                      target="_blank" rel="noopener"
                      @click.prevent="openManualLink(m.path)"
                    >
                      {{ m.title }}
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>


          <!-- ステーション（KDS） -->
          <div class="accordion accordion-flush my-2 d-none" id="accordionStations">
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
                    <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav({name:'mng-kds-dishup'})">
                      デシャップ
                    </a>
                    <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav({name:'mng-kds-kitchen'})">
                      キッチン
                    </a>
                    <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav({name:'mng-kds-drinker'})">
                      ドリンカー
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <!-- -------- フッタ ---------- -->
        <div class="footer d-flex flex-column gap-2">
          <!-- 広告 -->
          <div class="advertisement">
            <a href="https://studio-color.jp/" class="d-flex text-black justify-content-between align-items-center" target="_blank" rel="noopener">
              <div class="wrap d-flex flex-column">
                <span style="font-size: 12px;">キャスト撮影やコンテンツ制作なら</span>
                <span class="fw-bold fs-5">スタジオカラー</span>
              </div>
            </a>
          </div>
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

          <button class="btn btn-sm btn-outline-danger w-100" @click="logout">
            ログアウト
          </button>
          <StoreSwitcher />
          <DevRoleSwitcher />
          <div class="version text-muted small text-center w-100">
            v{{ APP_VERSION }}
          </div>
        </div>
      </aside>
    </div>
  </teleport>
</template>

<style scoped>
/* PC: 常時表示の固定サイドバー */
.manager-sidebar-pc {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  position: sticky;
  top: 0;
  left: 0;
  background: #fff;
  border-right: 1px solid #e9ecef;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.manager-sidebar-pc :deep(.aside) {
  padding: 1rem;
  flex: 1;
}
</style>
