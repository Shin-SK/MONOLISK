<!-- MenuSetting.vue（フル） -->
<script setup>
import { ref, onMounted, computed } from 'vue'
import { api, getStores, fetchMasters } from '@/api'

const stores  = ref([])
const storeId = ref(null)

const items = ref([])
const cats  = ref([])

const loading   = ref(false)
const error     = ref('')
const editRowId = ref(null)
const draft     = ref(resetDraft())

/* ───────── 絞り込み/ソート用 ───────── */
const selectedCatCode = ref('drink')  // 初期は drink
const norm = v => String(v ?? '').toLowerCase()

const catsSorted = computed(() => {
  const arr = [...cats.value]
  // drink 最上位 → 日本語名昇順
  arr.sort((a,b) => {
    const ad = norm(a.code) === 'drink'
    const bd = norm(b.code) === 'drink'
    if (ad && !bd) return -1
    if (!ad && bd) return 1
    return (a.name || '').localeCompare(b.name || '', 'ja')
  })
  return arr
})

const itemsView = computed(() => {
  const want = norm(selectedCatCode.value)
  const filtered = items.value.filter(it => {
    const c = it.category?.code ?? it.category ?? ''
    return want ? norm(c) === want : true         // 空＝全件
  })
  // 名前 → 通常価格 で安定ソート
  return filtered.slice().sort((a,b) => {
    const nameCmp = (a.name||'').localeCompare(b.name||'', 'ja')
    if (nameCmp) return nameCmp
    return (+a.price_regular||0) - (+b.price_regular||0)
  })
})

/* ───────── 小物 ───────── */
function resetDraft() {
  return {
    id: null,
    name: '',
    category: '',        // ItemCategory の code（文字列）
    price_regular: 0,
    price_late: '',
    duration_min: 0,
    apply_service: true,
    exclude_from_payout: false,
    track_stock: false,
  }
}

function catLabel(codeOrObj) {
  const code = typeof codeOrObj === 'object' ? codeOrObj?.code : codeOrObj
  const found = cats.value.find(c => norm(c.code) === norm(code))
  return found ? `${found.name}` : (code || '—')
}
const catValue = v => (typeof v === 'object' ? v.code : v)

/* ───────── マスター読込 ───────── */
async function loadCats() {
  try {
    const res = await api.get('billing/item-categories/')
    cats.value = Array.isArray(res.data?.results) ? res.data.results : res.data
  } catch {
    cats.value = []
  }
}

async function loadStoreAndItems() {
  error.value = ''
  loading.value = true
  try {
    stores.value = await getStores()
    storeId.value = stores.value[0]?.id ?? null
    if (!storeId.value) return
    const data = await fetchMasters(storeId.value)
    items.value = Array.isArray(data?.results) ? data.results : data
  } catch (e) {
    error.value = e?.response?.data?.detail || '読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

/* ───────── 行操作 ───────── */
function startCreate() {
  editRowId.value = 'new'
  draft.value = resetDraft()
  // 新規行のカテゴリを現在の絞り込みに合わせる
  draft.value.category = selectedCatCode.value || ''
}

function startEdit(row) {
  editRowId.value = row.id
  draft.value = {
    id: row.id,
    name: row.name ?? '',
    category: row.category?.code ?? row.category ?? '',
    price_regular: row.price_regular ?? 0,
    price_late: row.price_late ?? '',
    duration_min: row.duration_min ?? 0,
    apply_service: !!row.apply_service,
    exclude_from_payout: !!row.exclude_from_payout,
    track_stock: !!row.track_stock,
  }
}

function cancelEdit() {
  editRowId.value = null
  draft.value = resetDraft()
}

async function save() {
  const payload = {
    name: draft.value.name,
    category: catValue(draft.value.category),
    price_regular: +draft.value.price_regular || 0,
    price_late: draft.value.price_late === '' ? null : (+draft.value.price_late || 0),
    duration_min: +draft.value.duration_min || 0,
    apply_service: !!draft.value.apply_service,
    exclude_from_payout: !!draft.value.exclude_from_payout,
    track_stock: !!draft.value.track_stock,
    store_id: storeId.value,                // 念のため付ける（インターセプタと二重でもOK）
  }
  try {
    if (editRowId.value === 'new') {
      const res = await api.post('billing/item-masters/', payload)
      items.value.unshift(res.data)
    } else {
      const id = draft.value.id
      const res = await api.patch(`billing/item-masters/${id}/`, payload)
      const idx = items.value.findIndex(i => i.id === id)
      if (idx >= 0) items.value[idx] = res.data
    }
    cancelEdit()
  } catch (e) {
    console.error(e)
    alert(e?.response?.data?.detail || '保存に失敗しました')
  }
}

async function remove(row) {
  if (!confirm(`「${row.name}」を削除しますか？`)) return
  try {
    await api.delete(`billing/item-masters/${row.id}/`)
    items.value = items.value.filter(i => i.id !== row.id)
  } catch (e) {
    console.error(e)
    alert(e?.response?.data?.detail || '削除に失敗しました')
  }
}

/* ───────── 起動 ───────── */
onMounted(async () => {
  await loadCats()
  await loadStoreAndItems()

  // drink が存在しない or drink に該当アイテムが無い場合は最初の出せるカテゴリへ
  const hasDrinkCat  = cats.value.some(c => norm(c.code) === 'drink')
  const hasDrinkItem = items.value.some(it => norm(it.category?.code ?? it.category) === 'drink')
  if (!(hasDrinkCat && hasDrinkItem)) {
    // items から優先で拾い、無ければカテゴリ一覧の先頭
    const firstItemCat = items.value.find(it => it.category)?.category
    selectedCatCode.value =
      (typeof firstItemCat === 'object' ? firstItemCat?.code : firstItemCat)
      || cats.value[0]?.code
      || ''
  }
})
</script>

<template>
  <div>
    <div v-if="loading" class="text-muted">読み込み中…</div>
    <div v-else>
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h5 class="m-0">メニュー</h5>
        <button class="btn btn-primary" @click="startCreate" :disabled="editRowId">追加</button>
      </div>

      <!-- カテゴリ絞り込み -->
      <div class="d-flex align-items-center gap-2 mb-3">
        <label class="form-label m-0">カテゴリ</label>
        <select v-model="selectedCatCode" class="form-select" style="max-width: 260px;">
          <option value="">すべて表示</option>
          <option v-for="c in catsSorted" :key="c.code" :value="c.code">
            {{ c.name }}
          </option>
        </select>
      </div>

      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead class="table-light">
            <tr>
              <th style="width:18%">カテゴリ</th>
              <th>品名</th>
              <th class="text-end" style="width:12%">通常価格</th>
              <th class="text-end" style="width:12%">深夜価格</th>
              <th class="text-end" style="width:12%">時間(min)</th>
              <th style="width:18%">フラグ</th>
              <th style="width:12%"></th>
            </tr>
          </thead>

          <tbody>
            <!-- 新規行 -->
            <tr v-if="editRowId==='new'">
              <td>
                <select class="form-select" v-model="draft.category">
                  <option value="" disabled>選択</option>
                  <option v-for="c in catsSorted" :key="c.code" :value="c.code">
                    {{ c.name }}
                  </option>
                </select>
              </td>
              <td><input class="form-control" v-model="draft.name" /></td>
              <td><input class="form-control text-end" type="number" v-model.number="draft.price_regular" /></td>
              <td><input class="form-control text-end" type="number" v-model="draft.price_late" /></td>
              <td><input class="form-control text-end" type="number" step="5" v-model.number="draft.duration_min" /></td>
              <td>
                <div class="form-check form-check-inline">
                  <input class="form-check-input" type="checkbox" v-model="draft.apply_service" id="ns-new">
                  <label class="form-check-label" for="ns-new">サービス料</label>
                </div>
                <div class="form-check form-check-inline">
                  <input class="form-check-input" type="checkbox" v-model="draft.exclude_from_payout" id="np-new">
                  <label class="form-check-label" for="np-new">歩合対象外</label>
                </div>
                <div class="form-check form-check-inline">
                  <input class="form-check-input" type="checkbox" v-model="draft.track_stock" id="ts-new">
                  <label class="form-check-label" for="ts-new">在庫管理</label>
                </div>
              </td>
              <td class="text-end">
                <button class="btn btn-success btn-sm me-2" @click="save">保存</button>
                <button class="btn btn-outline-secondary btn-sm" @click="cancelEdit">キャンセル</button>
              </td>
            </tr>

            <!-- 既存行 -->
            <tr v-for="it in itemsView" :key="it.id">
              <!-- 編集中 -->
              <template v-if="editRowId===it.id">
                <td>
                  <select class="form-select" v-model="draft.category">
                    <option value="" disabled>選択</option>
                    <option v-for="c in catsSorted" :key="c.code" :value="c.code">
                      {{ c.name }}
                    </option>
                  </select>
                </td>
                <td><input class="form-control" v-model="draft.name" /></td>
                <td><input class="form-control text-end" type="number" v-model.number="draft.price_regular" /></td>
                <td><input class="form-control text-end" type="number" v-model="draft.price_late" /></td>
                <td><input class="form-control text-end" type="number" step="5" v-model.number="draft.duration_min" /></td>
                <td>
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" v-model="draft.apply_service" :id="'ns'+it.id">
                    <label class="form-check-label" :for="'ns'+it.id">サービス料</label>
                  </div>
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" v-model="draft.exclude_from_payout" :id="'np'+it.id">
                    <label class="form-check-label" :for="'np'+it.id">歩合対象外</label>
                  </div>
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" v-model="draft.track_stock" :id="'ts'+it.id">
                    <label class="form-check-label" :for="'ts'+it.id">在庫管理</label>
                  </div>
                </td>
                <td class="text-end">
                  <button class="btn btn-success btn-sm me-2" @click="save">保存</button>
                  <button class="btn btn-outline-secondary btn-sm" @click="cancelEdit">キャンセル</button>
                </td>
              </template>

              <!-- 表示 -->
              <template v-else>
                <td>{{ catLabel(it.category?.code ?? it.category) }}</td>
                <td>{{ it.name }}</td>
                <td class="text-end">¥{{ (+it.price_regular||0).toLocaleString() }}</td>
                <td class="text-end">¥{{ (+it.price_late||0).toLocaleString() }}</td>
                <td class="text-end">{{ it.duration_min || 0 }}</td>
                <td>
                  <span class="badge bg-secondary me-1" v-if="it.apply_service">サービス料</span>
                  <span class="badge bg-warning text-dark me-1" v-if="it.exclude_from_payout">歩合対象外</span>
                  <span class="badge bg-info text-dark" v-if="it.track_stock">在庫管理</span>
                </td>
                <td class="text-end">
                  <button class="btn btn-outline-primary btn-sm me-2" @click="startEdit(it)">編集</button>
                  <button class="btn btn-outline-danger btn-sm" @click="remove(it)">削除</button>
                </td>
              </template>
            </tr>

            <!-- データなし（絞り込み後） -->
            <tr v-if="!itemsView.length && !editRowId">
              <td colspan="7" class="text-center text-muted">対象カテゴリにアイテムがありません</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
    </div>
  </div>
</template>
