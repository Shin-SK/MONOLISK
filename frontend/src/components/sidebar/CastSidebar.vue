<!-- src/components/sidebar/CastSidebar.vue -->
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Avatar from '@/components/Avatar.vue'
import { useProfile } from '@/composables/useProfile'
import { useRoles } from '@/composables/useRoles'
import { useUser } from '@/stores/useUser'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import { closeOffcanvas } from '@/utils/bsOffcanvas'

async function nav(to){
  await router.push(to)
  closeOffcanvas('#castSidebar')
}


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
  <teleport to="body">
    <div
      id="castSidebar"
      class="offcanvas offcanvas-start"
      tabindex="-1"
      aria-labelledby="castSidebarLabel"
    >
    <div class="offcanvas-header">
      <button type="button" class="btn-close text-reset" @click="closeOffcanvas('#castSidebar')" aria-label="閉じる" />
    </div>

    <div class="aside offcanvas-body d-flex flex-column justify-content-between v-100">
      <div class="wrap d-flex flex-column gap-1">
          <a class="btn w-100 d-flex justify-content-start" href="#" @click.prevent="nav({name:'cast-mypage'})">
            マイページ
          </a>
          <a class="btn w-100 d-flex" href="#" @click.prevent="nav({name:'cast-profile'})">
            プロフィール編集
          </a>
      </div>

      <div class="footer d-flex flex-column gap-2">
        <div class="d-flex justify-content-between align-items-center mb-3">

          <div class="d-flex align-items-center gap-2">
            <Avatar :url="avatarURL" :size="40" class="rounded-circle"/> 
            <span>{{ displayName }}</span>
          </div>
          <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'cast-profile'})">
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
