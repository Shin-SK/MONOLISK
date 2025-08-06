<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="d-flex min-vh-100">
    <!-- サイドバー -->
    <aside
      class="border-end bg-white p-3"
      style="width: 220px;"
    >
      <h1 class="h5 mb-3">
        予約管理
      </h1>
      <nav class="nav flex-column">
        <RouterLink
          to="/reservation"
          class="nav-link"
        >
          予約一覧
        </RouterLink>
        <RouterLink
          to="/reservation/new"
          class="nav-link"
        >
          新規予約
        </RouterLink>
      </nav>
    </aside>

    <!-- メイン -->
    <main class="flex-fill p-4 overflow-auto">
      <router-view />
    </main>
  </div>
</template>
