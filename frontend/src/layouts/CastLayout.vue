<!-- src/layouts/DriverLayout.vue -->
<script setup>
import AppHeader   from '@/components/AppHeader.vue'
import { ref }     from 'vue'

const mode = ref('timeline')          // ヘッダー内で切替ボタン状態だけ持つ
</script>

<template>
  <div class="cast mypage min-vh-100 d-flex flex-column">
    <!-- ▽ ヘッダー -->
    <AppHeader />

    <!-- ▽ ページ本体 -->
    <main class="flex-fill container d-flex flex-column">
      <router-view />
    </main>
  </div>
</template>
