<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { IconUserSquare, IconClipboardList, IconSoup, IconBeer, IconChefHat, IconReceiptYen } from '@tabler/icons-vue'

const router = useRouter()
const route  = useRoute()
const me     = useUser()

const claims      = computed(() => me.me?.claims || [])
const canOperate  = computed(() => claims.value.includes('operate_orders'))
const canPL       = computed(() => ['view_pl_store','view_pl_multi'].some(c => claims.value.includes(c)))
const KDS_ENABLED = import.meta.env.VITE_KDS_ENABLED === 'true'
const go = (to) => router.push(to)
async function logout() {
  try { await userStore.logout?.() } finally { router.push('/login') }//★ログアウトしますか？のalartを入れたい
}
</script>

<template>
  <!-- ★ MainLayout から開くオフキャンバスはこのIDで -->
  <div id="staffSidebar" class="staff-sidebar offcanvas offcanvas-start" tabindex="-1" style="--bs-offcanvas-width:min(80vw,300px);">
    <div class="offcanvas-header">
      <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Close"/>
    </div>

    <div class="offcanvas-body d-flex flex-column gap-2">
      <!-- 常時 -->
      <button class="d-flex gap-2"
              data-bs-dismiss="offcanvas"
              :class="{ active: route.name==='staff-mypage' }"
              @click="go({ name:'staff-mypage' })">
        <IconUserSquare /> <span>マイページ</span>
      </button>

      <!-- オペレーション（operate_orders） -->
      <template v-if="canOperate">
        <hr class="my-2">
        <button class="d-flex gap-2"
                data-bs-dismiss="offcanvas"
                :class="{ active: route.name==='staff-order' }"
                @click="go({ name:'staff-order' })">
          <IconClipboardList /> <span>伝票（作成・編集）</span>
        </button>

        <!-- 会計（専用画面がまだ無ければ staff-order を流用） -->
        <button class="d-flex gap-2"
                data-bs-dismiss="offcanvas"
                :class="{ active: route.name==='staff-order' }"
                @click="go({ name:'staff-order' })">
          <IconReceiptYen /> <span>会計</span>
        </button>

        <template v-if="KDS_ENABLED">
          <div class="mt-2 small text-muted">KDS</div>
          <button class="btn btn-outline-secondary d-flex gap-2"
                  data-bs-dismiss="offcanvas"
                  :class="{ active: route.name==='staff-kds' && route.params.station==='kitchen' }"
                  @click="go({ name:'staff-kds', params:{station:'kitchen'} })">
            <IconChefHat /> <span>Kitchen</span>
          </button>
          <button class="btn btn-outline-secondary d-flex gap-2"
                  data-bs-dismiss="offcanvas"
                  :class="{ active: route.name==='staff-kds' && route.params.station==='drinker' }"
                  @click="go({ name:'staff-kds', params:{station:'drinker'} })">
            <IconBeer /> <span>Drinker</span>
          </button>
          <button class="btn btn-outline-secondary d-flex gap-2"
                  data-bs-dismiss="offcanvas"
                  :class="{ active: route.name==='staff-kds' && route.params.station==='dishup' }"
                  @click="go({ name:'staff-kds', params:{station:'dishup'} })">
            <IconSoup /> <span>Dishup</span>
          </button>
        </template>
        <button class="btn btn-outline-danger w-100" @click="logout">
          ログアウト
        </button>
      </template>

      <!-- PL系は出さない（URL直打ちはrouterの capsAny で403） -->
      <template v-if="false && canPL"></template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.btn.active{ border-color: var(--bs-primary); } 

.staff-sidebar{
  button{
    justify-content: start;
  }
}


</style>
