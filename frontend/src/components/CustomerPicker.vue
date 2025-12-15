<script setup>
import { ref, watch, onMounted } from 'vue'
import { useCustomers } from '@/stores/useCustomers'
import { fetchCustomerTags, createCustomerTag } from '@/api'

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
const tags     = ref([])        // タグ候補
const selectedTagIds = ref([])  // 選択中タグID
const newTagName = ref('')      // 新規タグ名

// 編集用フォーム（一部だけ編集しても v‑model で保持）
const form = ref({
  id: null, full_name: '', alias: '', phone: '', birthday: '', memo: '', tag_ids: [],
  has_bottle: false, bottle_shelf: '', bottle_memo: '',
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
    selectedTagIds.value = Array.isArray(obj?.tags) ? obj.tags.map(t => t.id) : []
    form.value = {
      ...obj,
      tag_ids: [...selectedTagIds.value],
      has_bottle: obj.has_bottle ?? false,
      bottle_shelf: obj.bottle_shelf ?? '',
      bottle_memo: obj.bottle_memo ?? '',
    }
  },
  { immediate: true }
)

onMounted(async () => {
  try {
    tags.value = await fetchCustomerTags()
  } catch (e) {
    console.error('failed to fetch tags', e)
    tags.value = []
  }
})

function toggleTag(id) {
  const idx = selectedTagIds.value.indexOf(id)
  if (idx >= 0) selectedTagIds.value.splice(idx, 1)
  else selectedTagIds.value.push(id)
  form.value.tag_ids = [...selectedTagIds.value]
}

function slugify(str) {
  const base = String(str || '').trim().toLowerCase()
  const slug = base
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)
  const suffix = Math.random().toString(36).slice(2, 6)
  return slug || `tag-${suffix}`
}

async function addNewTag() {
  const name = newTagName.value.trim()
  if (!name) return
  try {
    const tag = await createCustomerTag({ code: slugify(name), name, color: '#6c757d' })
    tags.value = [...tags.value, tag]
    if (tag.id != null) {
      selectedTagIds.value.push(tag.id)
      form.value.tag_ids = [...selectedTagIds.value]
    }
    newTagName.value = ''
  } catch (e) {
    console.error('failed to create tag', e)
    alert('タグの作成に失敗しました')
  }
}

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
  selectedTagIds.value = Array.isArray(obj?.tags) ? obj.tags.map(t => t.id) : []
  form.value = {
    ...obj,
    tag_ids: [...selectedTagIds.value],
    has_bottle: obj.has_bottle ?? false,
    bottle_shelf: obj.bottle_shelf ?? '',
    bottle_memo: obj.bottle_memo ?? '',
  }
  emit('update:modelValue', id)
  emit('picked', obj)
  kw.value = ''
  results.value = []
}

function newCustomer () {
  selected.value = null
  selectedTagIds.value = []
  form.value = {
    id: null, full_name: '', alias: '', phone: '', birthday: '', memo: '', tag_ids: [],
    has_bottle: false, bottle_shelf: '', bottle_memo: '',
  }
}

async function save () {
  form.value.tag_ids = [...selectedTagIds.value]
  const saved = await custStore.save(form.value)
  custStore.cache.set(saved.id, saved)
  selected.value = saved
  emit('update:modelValue', saved.id)
  emit('saved', saved)
  alert('保存しました')
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
        class="form-control bg-white"
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
      <div class="mb-3">
        <label class="form-label fw-bold small">氏名</label>
        <input v-model="form.full_name" class="form-control" />
      </div>
      <div class="mb-3">
        <label class="form-label fw-bold small">あだ名</label>
        <input v-model="form.alias" class="form-control" />
      </div>
      <div class="mb-3">
        <label class="form-label fw-bold small">電話番号</label>
        <input v-model="form.phone" class="form-control" />
      </div>
      <div class="mb-3">
        <label class="form-label fw-bold small">属性タグ</label>
        <div class="d-flex flex-wrap gap-2">
          <button
            v-for="tag in tags"
            :key="tag.id"
            type="button"
            class="badge rounded-pill"
            :class="selectedTagIds.includes(tag.id)
              ? 'bg-secondary text-white'
              : 'bg-white text-secondary border border-secondary'"
            @click="toggleTag(tag.id)"
          >
            {{ tag.name }}
          </button>
        </div>
        <div class="mt-3 row">
          <div class="col-8">
            <input
              v-model="newTagName"
              class="form-control w-100"
              placeholder="新しいタグ名を追加"
            />
          </div>
          <div class="col-4">
            <button class="btn btn-sm btn-outline-secondary w-100 h-100" type="button" @click="addNewTag">追加</button>
          </div>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label fw-bold small">誕生日</label>
        <input v-model="form.birthday" type="date" class="form-control" />
      </div>
      <div class="mb-3">
        <div class="d-flex align-items-center gap-2 mb-2">
          <label class="form-label fw-bold small mb-0">マイボトル</label>
          <div class="form-check form-switch">
            <input
              v-model="form.has_bottle"
              class="form-check-input"
              type="checkbox"
              id="hasBottleSwitch"
            />
            <label class="form-check-label small" for="hasBottleSwitch">
              {{ form.has_bottle ? 'あり' : 'なし' }}
            </label>
          </div>
        </div>
        <div v-if="form.has_bottle" class="ms-3">
          <div class="mb-2">
            <label class="form-label small">棚番号</label>
            <input v-model="form.bottle_shelf" class="form-control" placeholder="A-12" />
          </div>
          <div>
            <label class="form-label small">識別メモ</label>
            <textarea v-model="form.bottle_memo" rows="2" class="form-control" placeholder="シャトー・マルゴー 2015"></textarea>
          </div>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label fw-bold small">メモ</label>
        <textarea v-model="form.memo" rows="3" class="form-control"></textarea>
      </div>
      <div class="text-end">
        <button class="btn btn-sm btn-primary w-100" @click="save">保存</button>
      </div>
    </div>
  </div>

</template>