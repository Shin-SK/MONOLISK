<!-- src/components/sidebar/StaffSidebar.vue -->
<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { useRoles } from '@/composables/useRoles'
import { useProfile } from '@/composables/useProfile'
import Avatar from '@/components/Avatar.vue'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import { closeOffcanvas } from '@/utils/bsOffcanvas'

const router = useRouter()
const route  = useRoute()
const user   = useUser()
const { role, isSuper, hasRole } = useRoles()
const { displayName, avatarURL } = useProfile()

const canOperate = computed(() => hasRole(['staff','manager','owner'])) // 受注系
const canPL      = computed(() => hasRole(['manager','owner']) || isSuper.value)
const KDS_ENABLED = import.meta.env.VITE_KDS_ENABLED === 'true'

async function nav(to){
  await router.push(to)
  closeOffcanvas('#staffSidebar')           // ← self id を閉じる
}

async function logout() {
  if (!confirm('ログアウトしますか？')) return
  try { await user.logout?.() } finally { router.push('/login') }
}
</script>

<template>
  <teleport to="body">
    <div
      id="staffSidebar"
      class="staff-sidebar offcanvas offcanvas-start"
      tabindex="-1"
      style="--bs-offcanvas-width:min(100vw,300px);"
      aria-labelledby="staffSidebarLabel"
    >
      <div class="offcanvas-header">
        <!-- data-api でなく JS 統一 -->
        <button type="button" class="btn-close text-reset" @click="closeOffcanvas('#staffSidebar')" aria-label="閉じる" />
      </div>

      <div class="offcanvas-body d-flex flex-column gap-2">
        <div class="wrap d-flex flex-column h-100">

          <!-- 常時メニュー -->
          <a class="btn w-100 d-flex gap-2 justify-content-start border-0"
             href="#"
             :class="{ active: route.name==='staff-mypage' }"
             @click.prevent="nav({ name:'staff-mypage' })">
            <IconUserSquare /> <span>マイページ</span>
          </a>

          <template v-if="KDS_ENABLED">
            <div class="mt-auto mb-5">
              <div class="mt-2 small text-muted mb-2">KDS</div>
              <div class="d-flex flex-column gap-3">
                <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav('/kds/dishup')">
                  <IconSoup /> デシャップ
                </a>
                <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav('/kds/kitchen')">
                  <IconChefHat /> キッチン
                </a>
                <a class="nav-link ps-3 ms-1 bg-white" href="#" @click.prevent="nav('/kds/drinker')">
                  <IconBeer /> ドリンカー
                </a>
              </div>
            </div>
          </template>

        </div>

        <div class="footer d-flex flex-column gap-2">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <div class="d-flex align-items-center gap-2">
              <Avatar :url="avatarURL" :size="40" class="rounded-circle"/> 
              <span>{{ displayName }}</span>
            </div>
            <!-- プロフィールは staff 側へ -->
            <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'staff-profile'})">
              <IconEdit :size="16" class="text-secondary" />
            </a>
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
