<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { useRoles } from '@/composables/useRoles'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import { closeSidebar } from '@/utils/offcanvas'

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
  try { await user.logout?.() } finally { router.push('/login') }
}
</script>
<template>

  <teleport to="body">
  <div id="staffSidebar" class="staff-sidebar offcanvas offcanvas-start" tabindex="-1" style="--bs-offcanvas-width:min(80vw,300px);">
    <div class="offcanvas-header">
      <button class="btn-close" data-bs-dismiss="offcanvas" />
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


        <template v-if="KDS_ENABLED">
          <div class="mt-auto mb-5">
            <div class="mt-2 small text-muted mb-2">KDS</div>
            <div class="d-flex flex-column gap-3">
              <RouterLink class="nav-link ps-3 ms-1 bg-white" to="/kds/dishup"  @click="closeSidebar"><IconSoup /> デシャップ</RouterLink>
              <RouterLink class="nav-link ps-3 ms-1 bg-white" to="/kds/kitchen" @click="closeSidebar"> <IconChefHat />キッチン</RouterLink>
              <RouterLink class="nav-link ps-3 ms-1 bg-white" to="/kds/drinker" @click="closeSidebar"><IconBeer />ドリンカー</RouterLink>
            </div>
          </div>


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

        <DevRoleSwitcher class="mt-4 mb-2"/>

      </div>
    </div>
  </div>
  </teleport>
</template>

<style scoped lang="scss">
.btn.active{ border-color: var(--bs-primary); } 

.staff-sidebar{
  button{
    justify-content: start;
  }
}

.nav-link{
  display: flex;
  align-items: center;
  gap: 8px;
}

</style>
