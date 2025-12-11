<!-- App.vue -->
<script setup>
import { computed } from 'vue'
import { useLoading } from '@/stores/useLoading'

const loading = useLoading()
const globalLoading = computed(() => loading.globalLoading)
</script>

<template>

  <RouterView />
  <div class="cr">
    MONOLISK
  </div>

  <div v-if="globalLoading" class="global-loading">
    <div class="spinner"></div>
    <div class="mt-2 text-light fw-bold">読み込み中...</div>
  </div>
</template>

<style>

html, body {
  touch-action: manipulation;
}

.global-loading {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.global-loading .spinner {
  width: 56px;
  height: 56px;
  border: 6px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

</style>