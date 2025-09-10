<script setup>
import { ref, computed, onMounted } from 'vue'
import SidebarOffcanvas from '@/components/SidebarOffcanvas.vue'
import PullToRefresh from '@/components/PullToRefresh.vue'

const isPWA = ref(false)
const forcePTR = ref(false) // ← 一時的にブラウザでも有効化するフラグ

onMounted(() => {
  // PWA判定
  const m = window.matchMedia?.('(display-mode: standalone)')
  isPWA.value = !!(m && m.matches) || window.navigator.standalone === true
  try { m?.addEventListener?.('change', e => { isPWA.value = e.matches }) } catch {}

  // 強制ON: ?ptr=1 か localStorage.ptr=1 で有効
  const qs = new URLSearchParams(location.search)
  forcePTR.value = qs.get('ptr') === '1' || localStorage.getItem('ptr') === '1'

  // デバッグ用コンソールAPI（任意）
  if (import.meta.env.DEV) {
    window.ptrOn  = () => { localStorage.setItem('ptr','1'); location.reload() }
    window.ptrOff = () => { localStorage.removeItem('ptr');  location.reload() }
  }
})

const enablePTR = computed(() => isPWA.value || forcePTR.value)
const reload = () => window.location.reload()
</script>

<template>
  <PullToRefresh v-if="enablePTR" @refresh="reload">
    <SidebarOffcanvas />
    <RouterView />
    <div class="cr">MONOLISK</div>
  </PullToRefresh>

  <template v-else>
    <SidebarOffcanvas />
    <RouterView />
    <div class="cr">MONOLISK</div>
  </template>
</template>
