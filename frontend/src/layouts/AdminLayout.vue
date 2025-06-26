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
  <header class="header">

      <!-- アバター（メニュー開閉トグル） -->
	   <button class="avatar-icon btn p-0 border-0 bg-transparent"
        data-bs-toggle="offcanvas"
        data-bs-target="#appSidebar"
        aria-controls="appSidebar">
			<img  :src="userStore.avatar" class="rounded-circle" width="40" height="40"/>
		</button>

  </header>

  	<div id="appSidebar"
		class="offcanvas offcanvas-start"
		style="--bs-offcanvas-width: min(50vw, 300px);"
		tabindex="-1"
		aria-labelledby="appSidebarLabel">

		<div class="offcanvas-header">
			<button type="button" class="btn-close text-reset" data-bs-dismiss="offcanvas" aria-label="Close"></button>
		</div>

    <aside class="offcanvas-body aside d-flex flex-column justify-content-between vh-100">
      <div class="top">
        <h1 class="h1"><RouterLink to="/dashboard">管理者用</RouterLink></h1>

        <nav class="nav flex-column">
          <RouterLink to="/reservations">予約一覧</RouterLink>
          <RouterLink to="/customers"   >顧客</RouterLink>
          <RouterLink to="/casts"       >キャスト</RouterLink>
          <RouterLink to="/shifts">シフト管理</RouterLink>
          <RouterLink to="/closing"     >売上管理</RouterLink>
          <RouterLink to="/timeline"    >タイムライン</RouterLink>

        </nav>
      </div>

      <!-- ★ ログアウトリンク（シンプル版） -->
      
      <div class="bottom">
        <div class="user d-flex gap-2 align-items-center">
          <div class="avatar-icon">
            <img :src="userStore.avatar" class="rounded-circle" />
          </div>
          <div class="name">{{ userStore.name }}</div>
        </div>
        <button class="btn btn-outline-danger w-100 mt-4" @click.prevent="logout">ログアウト</button>
      </div>

    </aside>

	</div>


    <!-- ───────── メイン ───────── -->
    <main class="flex-fill p-4">
      <router-view />
    </main>
  </div>
</template>
