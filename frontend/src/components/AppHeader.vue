<script setup>
import { ref, computed } from 'vue'
import { useRouter }     from 'vue-router'
import { api }           from '@/api'
import { useUser }       from '@/stores/useUser'

/* ---------- state / helper ---------- */
const router    = useRouter()
const userStore = useUser()
const mode      = ref('timeline')               // タイムライン / リスト切替


const rootPath = computed(() =>
  userStore.isDriver ? '/driver' :
  userStore.isCast   ? '/cast'   : ''
)

/* ---------- 先に logout を宣言しておく ---------- */
async function logout () {
  try { await api.post('dj-rest-auth/logout/') }
  finally {
    userStore.clear()
    router.push('/login')
  }
}

/* ---------- ロール別メニュー ---------- */
const menuItems = computed(() => {
  const base   = [{ label:'プロフィール編集', action:()=>router.push(`${rootPath.value}/profile`) }]
  if (userStore.isCast)   base.push({ label:'売上', action:()=>router.push(`${rootPath.value}/sales`) })
  base.push({ label:'ログアウト', action:logout })
  return base
})

/* ---------- ナビボタン ---------- */
function goTimeline () { router.push(`${rootPath.value}/mypage`);            mode.value='timeline' }
function goList     () { router.push(`${rootPath.value}/mypage?view=list`); mode.value='list' }

/* ▼ 追加：表示名（display_name が無ければ username） */
const displayName = computed(() =>
  userStore.info?.display_name || userStore.info?.username || ''
)

</script>

<template>
  <header class="header">
    <div class="header__wrap container d-flex justify-content-between align-items-center">

      <!-- アバター（メニュー開閉トグル） -->
	   <button class="btn p-0 border-0 bg-transparent"
        data-bs-toggle="offcanvas"
        data-bs-target="#appSidebar"
        aria-controls="appSidebar">
			<img  :src="userStore.avatar" class="rounded-circle" width="40" height="40"/>
		</button>


      <!-- ページ切替ミニナビ -->
      <div class="mini-nav">
        <button class="btn btn-sm"
                :class="mode==='list' ? 'btn-primary':'btn-outline-primary'"
                @click="goList">
          <span class="material-symbols-outlined">list</span>
        </button>

        <button class="btn btn-sm"
                :class="mode==='timeline' ? 'btn-primary':'btn-outline-primary'"
                @click="goTimeline">
          <span class="material-symbols-outlined">view_timeline</span>
        </button>
      </div>
    </div>
  </header>

  <!-- ⬇︎ Off-Canvas メニュー -->
	<div id="appSidebar"
		class="offcanvas offcanvas-start"
		style="--bs-offcanvas-width: min(50vw, 300px);"
		tabindex="-1"
		aria-labelledby="appSidebarLabel">

		<div class="offcanvas-header">
			<button type="button" class="btn-close text-reset" data-bs-dismiss="offcanvas" aria-label="Close"></button>
		</div>

		<div class="offcanvas-body d-flex flex-column justify-content-between h-100 gap-3">
			<div class="wrap d-flex flex-column">
				<RouterLink class="btn btn-outline-primary w-100 d-flex justfy-content-start" to="/profile">プロフィール編集</RouterLink>

				<!-- v-if で切替（例） -->
				<RouterLink v-if="userStore.isCast" class="btn btn-outline-primary w-100 d-flex justfy-content-start" to="/cast/sales">売上</RouterLink>
			</div>
			<div class="bottom">
				<div class="user d-flex gap-2 align-items-center">
					<img  :src="userStore.avatar" class="rounded-circle" width="40" height="40"/>
					<div class="fw-semibold small">
						{{ displayName }}
					</div>
				</div>
				<!-- ☆ここにユーザー名とか本人がわかるやつがだしたい -->
				<button class="btn btn-outline-danger w-100" @click="logout">ログアウト</button>
			</div>
		</div>

	</div>
</template>
