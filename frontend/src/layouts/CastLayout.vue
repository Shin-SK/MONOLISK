<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUser } from '@/stores/useUser'
import { fetchBills } from '@/api'
import CastSidebar from '@/components/sidebar/CastSidebar.vue'
import Avatar from '@/components/Avatar.vue'
import { useCastEvents } from '@/stores/useCastEvents'
import { useProfile } from '@/composables/useProfile'
import RefreshAvatar from '@/components/RefreshAvatar.vue'

const router = useRouter()
const route  = useRoute()
const user   = useUser()
const { avatarURL, displayName } = useProfile() 


const candidates = ref([])      // 本指名で「自卓」注文できる Bill 候補
const singleBillId = computed(() => candidates.value.length === 1 ? candidates.value[0].id : null)
const hasSelfOrder = computed(() => candidates.value.length > 0)

/** 自分（me.cast_id）が在席中＆本指名の Bill を抽出 */
async function resolveSelfOrderTargets() {
  if (!user.me) await user.fetchMe?.()
  const meCastId = user.me?.cast_id
  if (!meCastId) { candidates.value = []; return }

  const data  = await fetchBills({ limit: 200 })
  const bills = Array.isArray(data.results) ? data.results : data
  const hits = []
  for (const b of bills) {
    const stays = b.stays || []
    const ok = stays.some(s =>
      (s.cast?.id === meCastId) &&
      (s.is_honshimei === true || s.stay_type === 'nom') &&
      !s.left_at
    )
    if (ok) hits.push({ id: b.id, tableName: b.table?.name || `#${b.table?.id || '-'}` })
  }
  candidates.value = hits
}

function goOrder() {
  if (singleBillId.value) {
    router.push({ path: '/cast/order', query: { bill: String(singleBillId.value) } })
  } else {
    router.push('/cast/order')
  }
}

/* ===== 伝票画面かどうか／キャストフッターの表示制御 ===== */
const isOrderPage     = computed(() => route.path.startsWith('/cast/order'))
const showCastFooter  = ref(!isOrderPage.value)
watch(isOrderPage, v => { showCastFooter.value = !v })
function toggleCastFooter(){
  if (isOrderPage.value) showCastFooter.value = !showCastFooter.value
}

function handleBillClosed(){ resolveSelfOrderTargets() }

function handleSelfOrderUpdate(){ resolveSelfOrderTargets() }

let castEvents = null
function handleEvents(evts){
  // どのイベントでもいったん候補を取り直す（十分に軽い）
  resolveSelfOrderTargets()
  // ついでにバッジ用の数が来たら反映したい場合はここで拾う
  // const e = Array.isArray(evts) ? evts.find(v => v?.type==='selforder_count') : null
  // if (e) selfOrderCount.value = e.count
}

onMounted(async () => {
  await resolveSelfOrderTargets()             // me取得も内包してるのでawait
  window.addEventListener('bill:closed', handleBillClosed)
  window.addEventListener('cast:selforder:update', handleSelfOrderUpdate)
  if (user.me?.cast_id) {
    castEvents = useCastEvents(user.me, handleEvents)
    castEvents.start()                        // ★開始
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('bill:closed', handleBillClosed)
  window.removeEventListener('cast:selforder:update', handleSelfOrderUpdate) 
  castEvents?.stop() 
})
watch(() => route.fullPath, (p) => {
  if (p.startsWith('/cast/')) resolveSelfOrderTargets()
})
</script>

<template>
  <div class="cast-layout min-vh-100 d-flex">
    <!-- ▼ キャスト共通フッター（伝票画面では右からスライド表示に切替） -->
    <div
      class="cast-footer d-flex"
     :class="{
       'is-orderpage': isOrderPage,
       'is-open': isOrderPage && showCastFooter
     }"
    >

        <!-- 右：マイページへ -->
        <RouterLink class="nav-link d-flex align-items-center justify-content-center" :to="{name: 'cast-mypage'}" title="マイページ">
          <RefreshAvatar />
        </RouterLink>

        <!-- 中央：自卓オーダー直行（伝票画面では非表示） -->
        <div class="position-absolute m-auto order-button" v-if="hasSelfOrder && !isOrderPage">
          <button
            class="btn btn-link p-0 border-0"
            @click="goOrder"
            aria-label="自卓オーダーへ"
          >
            <IconFileInvoice size="60" stroke="1.5" class="text-white rounded-circle bg-danger p-3" />
          </button>
        </div>
        <!-- 左：サイドバー -->
        <button
          class="avatar-icon btn p-0 border-0 bg-transparent"
          data-bs-toggle="offcanvas"
          data-bs-target="#castSidebar"
          aria-controls="castSidebar"
          title="メニュー"
        >
          <IconMenu2 />
        </button>

    </div>

    <!-- 伝票画面時のみ：右端にスライドトグル -->
    <button
      v-if="isOrderPage"
      class="toggle-tab btn shadow-sm"
      :class="{'opened': showCastFooter}"
      type="button"
      @click="toggleCastFooter"
      aria-label="キャストフッターの表示切替"
      title="キャストメニュー"
    >
      <IconChevronCompactLeft :size="18" />
    </button>

    <!-- オフキャンバス（サイドバー） -->
    <CastSidebar />

    <!-- 本体 -->
    <main class="flex-fill container d-flex flex-column">
      <router-view />
    </main>
  </div>
</template>

<style scoped lang="scss">
.cast-layout main{
  margin-bottom: 64px;
}

/* ── 通常：画面下いっぱいのフッター ── */
.cast-footer{
		padding: 8px 16px;
		position: fixed;
		bottom: 0;
		width: 100%;
		height: auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-direction: row;
		z-index: 999;
		background-color: white;
    .nav-link{
      width: 40px;
      height: 40px;
    }
    .order-button{
      left: 0;
      right: 0;
      bottom: 0;
      margin: auto;
      width: fit-content;
      .btn > svg {
        border-radius: 9999px;
        filter: drop-shadow(0 0px 5px rgba(0, 0, 0, 0.3))
      }
  }

  &.is-orderpage{
    width: auto;
    left: auto;
    right: .5rem;
    bottom: calc(80px + 80px + 2rem);
    border: 1px solid rgba(0,0,0,.08);
    border-radius: .75rem;
    padding: .75rem;
    box-shadow: 0 8px 24px rgba(0,0,0,.08);
    transform: translateX(110%);
    transition: transform .25s ease;
    &.is-open{
      transform: translateX(0);
    }
    .wrap{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
  }
}

/* 右端のスライド用タブ */
.toggle-tab{
  position: fixed;
  right: 0;
  bottom: calc(80px + 1rem);
  z-index: 99999;
  background: #fff !important;
  border: 1px solid rgba(0,0,0,.1);
  border-right: none;
  border-radius: .75rem 0 0 .75rem;
  padding: 32px 0px;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translateX(0);
}

.toggle-tab.opened svg{ transform: rotate(180deg); transition: transform .2s ease; }
</style>
