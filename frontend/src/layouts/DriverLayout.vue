<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="d-flex flex-column min-vh-100">
    <!-- ヘッダー -->
    <header class="navbar navbar-dark bg-primary">
      <div class="container-fluid">
        <span class="navbar-brand mb-0 h5">ドライバー</span>
        <RouterLink to="/login" class="btn btn-sm btn-light">ログアウト</RouterLink>
      </div>
    </header>

    <!-- 本体 -->
    <div class="d-flex flex-grow-1">
      <!-- メニュー -->
      <aside class="border-end p-3" style="width: 200px;">
        <nav class="nav flex-column">
          <RouterLink to="/driver"              class="nav-link">今日の配車</RouterLink>
          <RouterLink to="/driver/timeline"     class="nav-link">タイムライン</RouterLink>
        </nav>
      </aside>

      <!-- 詳細 -->
      <main class="flex-fill p-4 overflow-auto bg-white">
        <router-view />
      </main>
    </div>
  </div>
</template>
