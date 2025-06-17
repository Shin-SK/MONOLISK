<script setup>
import { RouterLink } from 'vue-router'
import { useUser }    from '@/stores/useUser'
const userStore = useUser()
</script>

<template>
  <div class="base admin d-flex min-vh-100">
    <!-- サイドバー -->
    <aside class="aside">
		<h1 class="h1">管理者用</h1>
      <nav class="nav flex-column">
        <RouterLink to="/reservations">予約一覧</RouterLink>
        <RouterLink to="/customers"   >顧客</RouterLink>
        <RouterLink to="/casts"       >キャスト</RouterLink>
        <RouterLink to="/closing"     >売上管理</RouterLink>
        <RouterLink to="/timeline"    >タイムライン</RouterLink>
      </nav>
      <div class="auth">
        <div class="icon">
            <img :src="userStore.avatar" class="rounded-circle"/>
        </div><!-- ユーザアイコン -->
        <div class="name">{{ userStore.name }}</div>
      </div>
    </aside>

    <!-- メイン -->
    <main class="flex-fill p-4">
      <router-view />
    </main>
  </div>
</template>
