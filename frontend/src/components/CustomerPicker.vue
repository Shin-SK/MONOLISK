<script setup>
import { ref, watch } from 'vue'
import { useCustomers } from '@/stores/useCustomers'

const props = defineProps({
  /** 選択中の顧客 ID。null なら未選択 */
  modelValue: Number,
})

const emit = defineEmits([
  'update:modelValue', // v‑model sync
  'picked',            // 既存客を選択した
  'saved',             // 新規／更新を完了した
])

/* ───────── state ───────── */
const kw       = ref('')        // 検索キーワード
const results  = ref([])        // 検索結果
const selected = ref(null)      // 選択中オブジェクト

// 編集用フォーム（一部だけ編集しても v‑model で保持）
const form = ref({
  id: null, full_name: '', alias: '', phone: '', birthday: '', memo: '',
})

const custStore = useCustomers()

/* ───────── sync ───────── */
watch(
  () => props.modelValue,
  async id => {
    if (!id) {
      selected.value = null
      return
    }
    // キャッシュ優先 → 無ければ fetch
    let obj = custStore.cache.get(id)
    if (!obj) obj = await custStore.fetchOne(id)
    custStore.cache.set(id, obj)
    selected.value = obj
    form.value = { ...obj }
  },
  { immediate: true }
)

/* ───────── handlers ───────── */
async function search () {
  if (!kw.value.trim()) return
  results.value = await custStore.search(kw.value, { silent: true })
}

function choose (id) {
  const obj =
    results.value.find(r => r.id === id) || custStore.cache.get(id)
  if (!obj) return
  custStore.cache.set(id, obj)
  selected.value = obj
  form.value = { ...obj }
  emit('update:modelValue', id)
  emit('picked', obj)
  kw.value = ''
  results.value = []
}

function newCustomer () {
  selected.value = null
  form.value = { id: null, full_name: '', alias: '', phone: '', birthday: '', memo: '' }
}

async function save () {
  const saved = await custStore.save(form.value)
  custStore.cache.set(saved.id, saved)
  selected.value = saved
  emit('update:modelValue', saved.id)
  emit('saved', saved)
}
</script>

<template>
  <div class="customer-picker d-grid gap-3 position-relative">
    <!-- 検索バー -->
    <div class="input-group position-relative">
      <input
        v-model="kw"
        @keyup.enter="search"
        placeholder="顧客検索"
        class="form-control"
      />
      <div class="d-flex align-items-center gap-1 position-absolute top-0 end-0 bottom-0" style="z-index: 10;">
        <button 
          @click="search">
          <IconSearch />
        </button>
        <button 
            @click="newCustomer">
          <IconCircleDashedPlus />
        </button>
      </div>
    </div>

    <!-- 結果リスト -->
    <ul v-if="results.length" class="list-group">
      <li
        v-for="c in results"
        :key="c.id"
        class="list-group-item list-group-item-action"
        @click="choose(c.id)"
      >
        {{ c.alias || c.full_name || 'No name' }}
        <small class="text-muted ms-2">{{ c.phone }}</small>
      </li>
    </ul>

    <!-- 詳細フォーム -->
    <div class="card p-3">
      <div class="mb-2">
        <label class="form-label">氏名</label>
        <input v-model="form.full_name" class="form-control" />
      </div>
      <div class="mb-2">
        <label class="form-label">あだ名</label>
        <input v-model="form.alias" class="form-control" />
      </div>
      <div class="mb-2">
        <label class="form-label">電話番号</label>
        <input v-model="form.phone" class="form-control" />
      </div>
      <div class="mb-2">
        <label class="form-label">誕生日</label>
        <input v-model="form.birthday" type="date" class="form-control" />
      </div>
      <div class="mb-2">
        <label class="form-label">メモ</label>
        <textarea v-model="form.memo" rows="3" class="form-control"></textarea>
      </div>
      <div class="text-end">
        <button class="btn btn-primary" @click="save">保存</button>
      </div>
    </div>
  </div>

</template>