<script setup>
import { computed } from 'vue'
import { api }           from '@/api'
import { useUser }       from '@/stores/useUser'
import { useRouter, useRoute } from 'vue-router'

/* ---------- state / helper ---------- */
const router    = useRouter()
const route     = useRoute()
const userStore = useUser()

// ✓ list / timeline / ''（どちらもハイライト無し）
const mode = computed(() => {
  if (route.query.view === 'list')      return 'list'
  if (route.path.includes('/mypage'))   return 'timeline'
  return ''                             // それ以外のページ
})

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


/* ---------- ナビボタン ---------- */
function goTimeline () { router.push(`${rootPath.value}/mypage`) }
function goList     () { router.push(`${rootPath.value}/mypage?view=list`) }

/* ▼ 追加：表示名（display_name が無ければ username） */
const displayName = computed(() =>
  userStore.info?.display_name || userStore.info?.username || ''
)

</script>

<template>
  <header class="header">
    <div class="header__wrap container d-flex justify-content-between align-items-center">

      <!-- アバター（メニュー開閉トグル） -->
	   <button class="avatar-icon btn p-0 border-0 bg-transparent"
        data-bs-toggle="offcanvas"
        data-bs-target="#appSidebar"
        aria-controls="appSidebar">
			<img  :src="userStore.avatar" class="rounded-circle" width="40" height="40"/>
		</button>


      <!-- ページ切替ミニナビ -->
      <div class="mini-nav">
        <button class="btn rounded-circle"
                :class="mode==='list' ? 'btn-primary':'btn-outline-primary'"
                @click="goList">
          <i class="bi bi-list-nested"></i>
        </button>

        <button class="btn rounded-circle"
                :class="mode==='timeline' ? 'btn-primary':'btn-outline-primary'"
                @click="goTimeline">
          <i class="bi bi-calendar-range"></i>
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
        <RouterLink
          class="btn btn-outline-primary w-100 d-flex justfy-content-start"
          :to="`${rootPath}/profile`"
        >
          プロフィール編集
        </RouterLink>

        <RouterLink
          v-if="userStore.isCast"
          class="btn btn-outline-primary w-100 d-flex justfy-content-start"
          :to="`${rootPath}/sales`"
        >
          売上
        </RouterLink>
			</div>
			<div class="bottom">
				<div class="user d-flex gap-2 align-items-center">
					<img  :src="userStore.avatar" class="rounded-circle" width="40" height="40"/>
					<div class="fw-semibold small">
						{{ displayName }}
					</div>
				</div>
				<button class="btn btn-outline-danger w-100" @click="logout">ログアウト</button>
			</div>
		</div>

	</div>
</template>
