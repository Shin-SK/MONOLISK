<!-- layouts/AdminLayout.vue など -->
<script setup>
import { RouterLink, useRouter } from 'vue-router'
import { api }        from '@/api'     // ← dj-rest-auth のエンドポイントを叩く
import { useUser }    from '@/stores/useUser'

const router     = useRouter()
const userStore  = useUser()

// ------- ログアウト -------
// 1) サーバへ POST /dj-rest-auth/logout/
// 2) Pinia のユーザー情報をクリア
// 3) ログイン画面へリダイレクト
async function logout () {
  try {
    await api.post('dj-rest-auth/logout/')
  } catch (e) {
    /* 既にセッション切れなど → 無視で OK */
  } finally {
    userStore.clear()
    router.push('/login')
  }
}
</script>

<template>
  <div class="base admin d-flex min-vh-100">
    <!-- ───────── サイドバー ───────── -->
    <aside class="aside">
      <h1 class="h1">管理者用</h1>

      <nav class="nav flex-column">
        <RouterLink to="/reservations">予約一覧</RouterLink>
        <RouterLink to="/customers"   >顧客</RouterLink>
        <RouterLink to="/casts"       >キャスト</RouterLink>
        <RouterLink to="/closing"     >売上管理</RouterLink>
        <RouterLink to="/timeline"    >タイムライン</RouterLink>
      </nav>

      <!-- ★ ログアウトリンク（シンプル版） -->
      <a class="logout-link" @click.prevent="logout">ログアウト</a>

      <div class="auth">
        <div class="icon">
          <img :src="userStore.avatar" class="rounded-circle" />
        </div>
        <div class="name">{{ userStore.name }}</div>
      </div>
    </aside>

    <!-- ───────── メイン ───────── -->
    <main class="flex-fill p-4">
      <router-view />
    </main>
  </div>
</template>
