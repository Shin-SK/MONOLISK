<!-- src/components/sidebar/CastSidebar.vue -->
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Avatar from '@/components/Avatar.vue'
import { useProfile } from '@/composables/useProfile'
import { useRoles } from '@/composables/useRoles'
import { useUser } from '@/stores/useUser'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'

const router = useRouter()
const { role } = useRoles()
const user = useUser()
const { displayName, avatarURL } = useProfile()

const isCast = computed(() => role.value === 'cast')

async function logout() {
  if (!confirm('ログアウトしますか？')) return
  try { await user.logout?.() } finally { router.push('/login') }
}
</script>

<template>
  <div
    id="castSidebar"
    class="offcanvas offcanvas-start"
    style="--bs-offcanvas-width: min(100vw,300px);"
    tabindex="-1"
    aria-labelledby="castSidebarLabel"
  >
    <div class="offcanvas-header">
      <button type="button" class="btn-close text-reset" data-bs-dismiss="offcanvas" aria-label="Close"/>
    </div>

    <div class="aside offcanvas-body d-flex flex-column justify-content-between v-100">
      <div class="wrap d-flex flex-column gap-4">
        <RouterLink class="btn w-100 d-flex justify-content-start" :to="{name: 'cast-mypage'}">
          マイページ
        </RouterLink>
        <RouterLink class="btn w-100 d-flex" :to="{name:'cast-profile'}">
          プロフィール編集
        </RouterLink>
        <RouterLink v-if="isCast" class="btn w-100 d-flex" :to="'/cast/sales'">
          売上
        </RouterLink>
      </div>

      <div class="footer d-flex flex-column gap-2">
        <DevRoleSwitcher sidebarId="castSidebar" />
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
