<script setup>
import { ref, computed, watch } from 'vue'
import { fetchSubstituteItems, addSubstituteItem, deleteSubstituteItem } from '@/api'

const props = defineProps({
  billId:           { type: Number, default: null },
  catOptions:       { type: Array, default: () => [] },
  masters:          { type: Array, default: () => [] },
  servedByOptions:  { type: Array, default: () => [] },
  billCustomers:    { type: Array, default: () => [] },
  readonly:         { type: Boolean, default: false },
})

const emit = defineEmits(['updated'])

/* ---- state ---- */
const items = ref([])
const loading = ref(false)
const saving = ref(false)

const selectedCat = ref(null)
const selectedMasterId = ref(null)
const selectedCastId = ref(null)
const selectedCustomerId = ref(null)
const qty = ref(1)

/* ---- computed ---- */
const filteredMasters = computed(() => {
  if (!selectedCat.value) return props.masters
  return props.masters.filter(m => m.category?.code === selectedCat.value)
})

const canAdd = computed(() =>
  props.billId && selectedMasterId.value && selectedCastId.value && qty.value >= 1
)

const yen = n => `\u00A5${(Number(n || 0)).toLocaleString()}`

/* ---- load ---- */
async function loadItems() {
  if (!props.billId) return
  loading.value = true
  try {
    items.value = await fetchSubstituteItems(props.billId)
  } catch (e) {
    console.error('substitute load failed', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.billId, (v) => { if (v) loadItems() }, { immediate: true })

/* ---- add ---- */
async function handleAdd() {
  if (!canAdd.value) return
  saving.value = true
  try {
    const payload = {
      item_master_id: Number(selectedMasterId.value),
      cast_id: Number(selectedCastId.value),
      qty: Number(qty.value),
    }
    if (selectedCustomerId.value) {
      payload.customer_id = Number(selectedCustomerId.value)
    }
    await addSubstituteItem(props.billId, payload)
    // reset
    selectedMasterId.value = null
    qty.value = 1
    await loadItems()
    emit('updated')
  } catch (e) {
    console.error('substitute add failed', e)
    alert('立替追加に失敗しました: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

/* ---- delete ---- */
async function handleDelete(itemId) {
  if (!confirm('この立替明細を削除しますか？')) return
  try {
    await deleteSubstituteItem(props.billId, itemId)
    await loadItems()
    emit('updated')
  } catch (e) {
    console.error('substitute delete failed', e)
    alert('削除に失敗しました')
  }
}
</script>

<template>
  <div class="substitute-panel p-2">
    <h6 class="mb-2 fw-bold">立替</h6>

    <!-- 入力フォーム -->
    <div v-if="!props.readonly" class="mb-3 border rounded p-2 bg-light">
      <!-- カテゴリ -->
      <div class="mb-2">
        <label class="form-label small mb-1">カテゴリ</label>
        <select v-model="selectedCat" class="form-select form-select-sm">
          <option :value="null">全て</option>
          <option v-for="c in catOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
      </div>

      <!-- 商品 -->
      <div class="mb-2">
        <label class="form-label small mb-1">商品 <span class="text-danger">*</span></label>
        <select v-model="selectedMasterId" class="form-select form-select-sm">
          <option :value="null" disabled>選択してください</option>
          <option v-for="m in filteredMasters" :key="m.id" :value="m.id">
            {{ m.name }} ({{ yen(m.price_regular || m.price || 0) }})
          </option>
        </select>
      </div>

      <!-- キャスト -->
      <div class="mb-2">
        <label class="form-label small mb-1">キャスト <span class="text-danger">*</span></label>
        <select v-model="selectedCastId" class="form-select form-select-sm">
          <option :value="null" disabled>選択してください</option>
          <option v-for="c in servedByOptions" :key="c.id" :value="c.id">{{ c.label }}</option>
        </select>
      </div>

      <!-- 顧客 -->
      <div class="mb-2">
        <label class="form-label small mb-1">顧客（任意）</label>
        <select v-model="selectedCustomerId" class="form-select form-select-sm">
          <option :value="null">なし</option>
          <option v-for="c in billCustomers" :key="c.id" :value="c.id">
            {{ c.alias || c.full_name || c.name || `#${c.id}` }}
          </option>
        </select>
      </div>

      <!-- 数量 -->
      <div class="mb-2">
        <label class="form-label small mb-1">数量</label>
        <input v-model.number="qty" type="number" min="1" class="form-control form-control-sm" style="width:80px" />
      </div>

      <button
        class="btn btn-sm btn-primary w-100"
        :disabled="!canAdd || saving"
        @click="handleAdd"
      >{{ saving ? '追加中...' : '立替を追加' }}</button>
    </div>

    <!-- 一覧 -->
    <div v-if="loading" class="text-muted small">読込中...</div>
    <div v-else-if="!items.length" class="text-muted small">立替明細なし</div>
    <div v-else class="table-responsive">
      <table class="table table-sm table-bordered align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th>商品</th>
            <th class="text-center">数量</th>
            <th>キャスト</th>
            <th>顧客</th>
            <th class="text-end">立替額</th>
            <th v-if="!props.readonly"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in items" :key="it.id">
            <td>{{ it.item_master?.name || it.name }}</td>
            <td class="text-center">{{ it.qty }}</td>
            <td>{{ it.cast?.stage_name || '—' }}</td>
            <td>{{ it.customer?.name || '—' }}</td>
            <td class="text-end">{{ yen(it.substitute_amount) }}</td>
            <td v-if="!props.readonly" class="text-center">
              <button class="btn btn-outline-danger btn-sm py-0 px-1" @click="handleDelete(it.id)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
