<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="d-flex flex-column min-vh-100 bg-light">
    <!-- トップバー -->
    <header class="navbar navbar-expand bg-danger navbar-dark">
      <div class="container-fluid">
        <span class="navbar-brand h5 mb-0">キャスト</span>
        <RouterLink to="/login" class="btn btn-sm btn-light">ログアウト</RouterLink>
      </div>
    </header>

    <!-- コンテンツ -->
    <main class="flex-fill p-4">
      <router-view />
    </main>

    <!-- フッタータブ（モバイル向け） -->
    <nav class="nav nav-tabs nav-fill fixed-bottom d-md-none">
      <RouterLink to="/cast/timeline" class="nav-link">タイムライン</RouterLink>
    </nav>
  </div>
</template>
