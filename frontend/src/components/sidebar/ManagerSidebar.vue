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

          <div class="d-flex flex-column mb-4 pb-4 border-bottom gap-3">
            <!-- ダッシュボード -->
            <a class="nav-link bg-white d-flex align-items-center gap-1 fs-5" href="#" @click.prevent="nav({name:'mng-dashboard'})">
              <IconHome /><span class="lh-1">ホーム</span>
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
            キャストシフト
          </a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-cast-sales'})">
            キャスト売上
          </a>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-ranking'})">
            ランキング
          </a>

          <!-- 顧客 -->
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'mng-customers'})">
            顧客情報
          </a>

<!-- 
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'Payroll'})">
            給与計算
          </a> -->

          <!-- 設定（ManagerLayout配下の /settings） -->
          <a class="nav-link mt-2 bg-white" href="#" @click.prevent="nav({name:'settings'})">
            設定
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
          <div class="">
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

          <button class="btn btn-outline-danger w-100" @click="logout">
            ログアウト
          </button>
          <StoreSwitcher class="mt-5" />
          <DevRoleSwitcher class="mt-1 mb-2"/>
          <div class="version text-muted small text-center w-100">
            v{{ APP_VERSION }}
          </div>
        </div>
      </aside>
    </div>
  </teleport>
</template>
