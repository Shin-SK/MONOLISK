<script setup>
import { useRoute, useRouter } from 'vue-router'
import Avatar from '@/components/Avatar.vue'
import { useAuth } from '@/stores/useAuth'
import { useProfile } from '@/composables/useProfile'
import DevRoleSwitcher from '@/components/DevRoleSwitcher.vue'
import StoreSwitcher from '@/components/StoreSwitcher.vue'
import { closeOffcanvas } from '@/utils/bsOffcanvas'

async function nav(to){
  await router.push(to)
  closeOffcanvas('#ownerSidebar')
}

const router = useRouter()
const route  = useRoute()
const { displayName, avatarURL } = useProfile()


const auth = useAuth()
async function logout () {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <teleport to="body">
    <div
      id="ownerSidebar"
      class="offcanvas offcanvas-start"
      tabindex="-1"
      aria-labelledby="ownerSidebarLabel"
    >
      <div class="offcanvas-header bg-white">
        <button class="btn-close" data-bs-dismiss="offcanvas" aria-label="閉じる" />
      </div>

      <aside class="aside offcanvas-body d-flex flex-column justify-content-between vh-100">
        <nav class="nav flex-column h-100">
          <div class="wrap">
            <a class="nav-link bg-white" href="#" @click.prevent="nav({name:'owner-dashboard'})">マイページ</a>
          </div>

          <div class="mt-auto">
            <a href="https://studio-color.jp/" class="d-flex text-black justify-content-between align-items-center" target="_blank" rel="noopener">
              <div class="wrap d-flex flex-column">
                <span style="font-size: 12px;">キャスト撮影やコンテンツ制作なら</span>
                <span class="fw-bold fs-5">スタジオカラー</span>
              </div>
            </a>
          </div>
        </nav>

        <div class="mt-auto border-top pt-3 d-flex flex-column gap-2">
          <div class="d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-2">
              <Avatar :url="avatarURL" :size="40" class="rounded-circle"/>
              <span>{{ displayName }}</span>
            </div>
            <RouterLink class="nav-link bg-white" :to="{name:'owner-profile'}" @click.prevent="nav({name:'owner-profile'})">
              <IconEdit :size="16" class="text-secondary" />
            </RouterLink>
          </div>
          <button class="btn btn-sm btn-outline-danger w-100" @click.prevent="logout">ログアウト</button>
          <StoreSwitcher class="" />
          <DevRoleSwitcher class="mb-2"/>
        </div>
      </aside>
    </div>
  </teleport>
</template>
