<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUser } from '@/stores/useUser'
import StaffSidebar from '@/components/sidebar/StaffSidebar.vue'
import Avatar from '@/components/Avatar.vue'

const route  = useRoute()
const router = useRouter()
const user   = useUser()

const avatarUrl = computed(() =>
  user.avatar || user.me?.avatar || user.me?.profile_image || '')

const pageTitle = computed(() => route.meta?.title || 'STAFF')
function go(name, params){ router.push({ name, params }) }
</script>

<template>
  <div class="staff-layout min-vh-100 d-flex flex-column">
    <!-- ヘッダー（簡素） -->
    <header class="border-bottom bg-white">
      <div class="container d-flex align-items-center justify-content-between py-2">
        <h1 class="h5 m-0">{{ pageTitle }}</h1>
        <button
          class="btn p-0 border-0 bg-transparent"
          data-bs-toggle="offcanvas"
          data-bs-target="#staffSidebar"
          aria-controls="staffSidebar"
        >
          <Avatar :url="avatarUrl" :size="32" class="rounded-circle"/>
        </button>
      </div>
    </header>

    <!-- 本体 -->
    <main class="flex-fill container py-3 overflow-auto">
      <router-view />
    </main>

    <!-- 固定フッター（スタッフ用） -->
    <footer class="staff-footer d-md-none">
      <div class="nav nav-pills nav-fill small gap-2 pills-flat">
        <button type="button" class="nav-link d-flex flex-column"
                :class="{active: route.name==='staff-mypage'}"
                @click="go('staff-mypage')">
          <IconUserSquare /><span>MY</span>
        </button>
        <button type="button" class="nav-link d-flex flex-column"
                :class="{active: route.name==='staff-order'}"
                @click="go('staff-order')">
          <IconClipboardList /><span>伝票</span>
        </button>
        <button type="button" class="nav-link d-flex flex-column"
                :class="{active: route.name==='staff-kds'}"
                @click="go('staff-kds', {station:'kitchen'})">
          <IconSoup /><span>KDS</span>
        </button>
        <!-- ルートを有効化したら使える -->
        <!--
        <button type="button" class="nav-link d-flex flex-column"
                :class="{active: route.name==='staff-cashier'}"
                @click="go('staff-cashier')">
          <IconReceiptYen /><span>会計</span>
        </button>
        -->
      </div>
    </footer>

    <!-- サイドバー -->
    <StaffSidebar />
  </div>
</template>

<style scoped>
.staff-footer{
  position: fixed; left: 0; right: 0; bottom: 0;
  background: #fff; border-top: 1px solid #eee;
  padding: .5rem max(env(safe-area-inset-left), .75rem)
           calc(.5rem + env(safe-area-inset-bottom))
           max(env(safe-area-inset-right), .75rem);
  z-index: 1040;
}
.pills-flat{ --bs-nav-pills-link-active-bg:#fff; --bs-nav-pills-link-active-color:#000; }
.pills-flat .nav-link{ background:#fff; color:#a9a9a9; border-radius:.75rem; }
.pills-flat .nav-link.active{ color:#000; font-weight:700; }
</style>
