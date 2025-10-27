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
  return String(selectedSid.value) === String(currentSid.value) ? '適用済み' : '更新'
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
  if (!canApply.value) return
  applying.value = true
  try {
    // 1) サーバ側の“現在店舗”を切替（/meも再取得）
    const me = await switchStore(selectedSid.value)
    u.me = me
    currentSid.value = String(selectedSid.value)
    localStorage.setItem('store_id', currentSid.value)

    // 2) 全体通知（各Piniaで reset→fetch などが走る）
    notifyStoreChanged(currentSid.value)

    // 3) 主要ストアは明示的に更新（体感向上）
    tables?.reset(); await tables?.fetch(true)
    casts?.reset?.();  await casts?.fetch?.(true)
    items?.reset?.();  await items?.fetch?.(true)

    // 4) 今いるURLのまま。最後にサイドバーを閉じる
    closeOffcanvas(props.offcanvas)   // ★ 追加：オフキャンバスを閉じる
  } catch (e) {
    console.error('[StoreSwitcher] apply failed', e)
  } finally {
    applying.value = false
  }
}
</script>

<template>
  <div v-if="visible" class="row g-2 align-items-center mt-1 mb-2">
    <div class="col-9">
      <select
        class="form-select w-100"
        v-model="selectedSid"
        @change="onSelectChange"
        :disabled="loadingList || applying"
      >
        <option v-for="s in stores" :key="s.id" :value="String(s.id)">
          {{ s.name || s.display_name || ('#' + s.id) }}
        </option>
      </select>
    </div>

	<div class="col-3 d-flex align-items-center">
	<button
		class="btn btn-sm w-100"
		:class="['btn-outline-secondary', { 'disabled': !canApply, 'pe-none': !canApply }]"
		:aria-disabled="!canApply ? 'true' : 'false'"
		@click="canApply && apply()"
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
