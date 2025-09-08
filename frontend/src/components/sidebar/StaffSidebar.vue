<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { IconUserSquare, IconClipboardList, IconSoup, IconBeer, IconChefHat, IconReceiptYen } from '@tabler/icons-vue'
import { useRoles } from '@/composables/useRoles'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'

const { role, isSuper, hasRole } = useRoles()

const router = useRouter()
const route  = useRoute()
const user   = useUser()

const { displayName, avatarURL } = useProfile()
const canOperate = computed(() => hasRole(['staff','manager','owner'])) // 受注系
const canPL      = computed(() => hasRole(['manager','owner']) || isSuper.value)

const KDS_ENABLED = import.meta.env.VITE_KDS_ENABLED === 'true'
const go = (to) => router.push(to)

async function logout() {
  if (!confirm('ログアウトしますか？')) return
  try { await userStore.logout?.() } finally { router.push('/login') }
}
</script>
<template>
  <!-- ★ MainLayout から開くオフキャンバスはこのIDで -->
  <div id="staffSidebar" class="staff-sidebar offcanvas offcanvas-start" tabindex="-1" style="--bs-offcanvas-width:min(80vw,300px);">
    <div class="offcanvas-header">
      <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Close"/>
    </div>

    <div class="offcanvas-body d-flex flex-column gap-2 ">
      <div class="wrap d-flex flex-column h-100">

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
          <div class="mt-auto mb-5">
            <div class="mt-2 small text-muted mb-2">KDS</div>
            <div class="d-flex flex-column gap-3">
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
            </div>
          </div>


        </template>
      </template>

      <!-- PL系は出さない（URL直打ちはrouterの capsAny で403） -->
      <template v-if="false && canPL"></template>
        
      </div>

      <div class="footer d-flex flex-column gap-2">
        <div class="d-flex justify-content-between align-items-center mb-3">

          <div class="d-flex align-items-center gap-2">
            <Avatar :url="avatarURL" :size="40" class="rounded-circle"/> 
            <span>{{ displayName }}</span>
          </div>
          <RouterLink class="nav-link bg-white" :to="{name: 'owner-profile'}" @click="closeSidebar"><IconEdit :size="16" class="text-secondary" /></RouterLink>
        </div>
        
        <button class="btn btn-outline-danger w-100" @click="logout">
          ログアウト
        </button>
      </div>
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
