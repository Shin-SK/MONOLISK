<!-- src/components/StoreSwitcher.vue（丸ごと置換） -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUser } from '@/stores/useUser'
import { useRoles } from '@/composables/useRoles'
import { listMyStores, switchStore } from '@/api'
import { notifyStoreChanged } from '@/stores/storeScope'
import { closeOffcanvas } from '@/utils/bsOffcanvas'   // ★ 追加

// 依存データ（任意）
import { useTables } from '@/stores/useTables'
import { useCasts } from '@/stores/useCasts'
import { useMasters } from '@/stores/useMasters'

// ★ どのオフキャンバスを閉じるか指定可能（既定 '#managerSidebar'）
const props = defineProps({ offcanvas: { type: String, default: '#managerSidebar' } })

const u = useUser()
const { homePath } = useRoles() // 遷移はしないが既存依存のため残置

const tables = useTables()
const casts  = useCasts?.() || null
const items  = useMasters?.() || null

const stores       = ref([])
const currentSid   = ref(localStorage.getItem('store_id') || '')
const selectedSid  = ref(currentSid.value) // 選択しただけでは切替しない
const loadingList  = ref(false)
const applying     = ref(false)

const isSuper  = computed(() => !!u.me?.is_superuser)
const isOwner  = computed(() => u.me?.current_role === 'owner')
const visible  = computed(() => (isSuper.value || isOwner.value) && stores.value.length > 0)

const canApply = computed(() =>
  !applying.value && selectedSid.value && String(selectedSid.value) !== String(currentSid.value)
)

const buttonLabel = computed(() => {
  if (applying.value) return '更新中…'
  return String(selectedSid.value) === String(currentSid.value) ? '適用済' : '更新'
})

onMounted(async () => {
  try {
    loadingList.value = true
    stores.value = await listMyStores()
    if (!selectedSid.value && stores.value[0]) {
      selectedSid.value = String(stores.value[0].id)
    }
  } catch (e) {
    console.warn('[StoreSwitcher] failed to load stores', e)
  } finally {
    loadingList.value = false
  }
})

function onSelectChange () {
  // 即切替しない（選択だけ）
}

async function apply () {
  applying.value = true
  const sid = String(selectedSid.value || '')
  console.log('[SWITCHER] apply start', { sid_before: localStorage.getItem('store_id'), selectedSid: sid })

  try {
    // A) 先にローカル確定（リロード後も反映）
    if (sid) {
      localStorage.setItem('store_id', sid)
      currentSid.value = sid
      notifyStoreChanged(sid)
      console.log('[SWITCHER] set store_id (localStorage)', sid)
    } else {
      console.warn('[SWITCHER] empty sid; fallback to existing')
    }

    // B) サーバ側スイッチ（失敗しても必ずリロードは行う）
    try {
      const me = await switchStore(sid)
      u.me = me
      console.log('[SWITCHER] switchStore OK', { sid })
    } catch (e) {
      console.warn('[SWITCHER] switchStore failed (will reload anyway)', e)
    }

    // C) サイドバーを閉じて即リロード（__sid は1個だけ付け直す）
    closeOffcanvas(props.offcanvas)
    const url = new URL(window.location.href)
    url.searchParams.delete('__sid') // 既存を全部削除
    url.searchParams.append('__sid', `${currentSid.value}-${Date.now()}`)
    console.log('[SWITCHER] reload replace ->', url.toString())
    window.location.replace(url.toString()) // これ1発でOK。setTimeout不要
  } finally {
    applying.value = false
  }
}


</script>

<template>
  <div v-if="visible" class="row g-2 align-items-center">
    <div class="col-8">
      <select
        class="form-select form-select-sm w-100"
        v-model="selectedSid"
        @change="onSelectChange"
        :disabled="loadingList || applying"
      >
        <option v-for="s in stores" :key="s.id" :value="String(s.id)">
          {{ s.name || s.display_name || ('#' + s.id) }}
        </option>
      </select>
    </div>

	<div class="col-4 d-flex align-items-center">
		<button
		type="button"
		class="btn btn-sm w-100 h-100"
		:class="['btn-outline-secondary', { 'disabled': !canApply, 'pe-none': !canApply }]"
		:aria-disabled="!canApply ? 'true' : 'false'"
		@click="apply"
		title="選択中の店舗に切り替える（現在のページのまま再読込）"
		style="white-space: nowrap;"
		>
		{{ buttonLabel }}
		</button>
	</div>

  </div>
</template>

<style scoped>
.form-select { min-width: 10rem; }
</style>
