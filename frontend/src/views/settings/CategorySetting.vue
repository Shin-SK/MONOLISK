<!-- CategorySetting.vue - カテゴリ表示順の並び替え -->
<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api'

const cats    = ref([])
const loading = ref(false)
const saving  = ref(false)
const error   = ref('')
const message = ref('')

// 表示用にソート（sort_order 昇順 → code 昇順）
const sorted = computed(() => {
  return [...cats.value].sort((a, b) => {
    const ao = Number(a.sort_order ?? 0)
    const bo = Number(b.sort_order ?? 0)
    if (ao !== bo) return ao - bo
    return String(a.code || '').localeCompare(String(b.code || ''))
  })
})

async function load() {
  error.value = ''
  message.value = ''
  loading.value = true
  try {
    const res = await api.get('billing/item-categories/')
    const data = Array.isArray(res.data?.results) ? res.data.results : res.data
    cats.value = Array.isArray(data) ? data : []
  } catch (e) {
    error.value = e?.response?.data?.detail || 'カテゴリの読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

function move(index, delta) {
  // sorted 表示上のインデックスで入れ替え、実体の sort_order を更新
  const arr = sorted.value
  const target = arr[index]
  const swap   = arr[index + delta]
  if (!target || !swap) return

  // cats.value 上の実体を取得
  const ti = cats.value.findIndex(c => c.code === target.code)
  const si = cats.value.findIndex(c => c.code === swap.code)
  if (ti < 0 || si < 0) return

  // sort_order を入れ替え
  const to = Number(cats.value[ti].sort_order ?? 0)
  const so = Number(cats.value[si].sort_order ?? 0)
  cats.value[ti] = { ...cats.value[ti], sort_order: so }
  cats.value[si] = { ...cats.value[si], sort_order: to }
}

function moveUp(index)   { move(index, -1) }
function moveDown(index) { move(index, +1) }

async function save() {
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    // 現在の表示順 (sorted) でコード列を送信
    const order = sorted.value.map(c => c.code)
    const res = await api.post('billing/item-categories/reorder/', { order })
    const data = res.data?.categories
    if (Array.isArray(data)) {
      cats.value = data
    }
    message.value = '並び順を保存しました'
  } catch (e) {
    error.value = e?.response?.data?.detail || '保存に失敗しました'
  } finally {
    saving.value = false
  }
}

function reload() {
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div v-if="loading" class="text-muted">読み込み中…</div>
    <div v-else>
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h5 class="m-0">カテゴリ表示順</h5>
        <div class="d-flex gap-2">
          <button class="btn btn-outline-secondary btn-sm" @click="reload" :disabled="saving">再読込</button>
          <button class="btn btn-primary btn-sm" @click="save" :disabled="saving">
            {{ saving ? '保存中…' : '並び順を保存' }}
          </button>
        </div>
      </div>

      <p class="small text-muted mb-3">
        注文画面などのカテゴリ表示順を変更できます。<br>
        ↑↓ボタンで並び替え、「並び順を保存」で確定します。<br>
        カテゴリ自体の追加・削除・コード変更は運営に依頼してください。
      </p>

      <div v-if="message" class="alert alert-success py-2">{{ message }}</div>
      <div v-if="error"   class="alert alert-danger py-2">{{ error }}</div>

      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead class="table-light">
            <tr>
              <th style="width:80px">表示順</th>
              <th>カテゴリ名</th>
              <th style="width:180px">コード</th>
              <th style="width:120px">伝票表示</th>
              <th style="width:150px">並び替え</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(c, i) in sorted" :key="c.code">
              <td class="text-muted">{{ c.sort_order ?? 0 }}</td>
              <td>{{ c.name }}</td>
              <td><code>{{ c.code }}</code></td>
              <td>
                <span v-if="c.show_in_menu" class="badge bg-success">ON</span>
                <span v-else class="badge bg-secondary">OFF</span>
              </td>
              <td>
                <button class="btn btn-outline-secondary btn-sm me-1"
                        :disabled="i === 0 || saving"
                        @click="moveUp(i)">↑</button>
                <button class="btn btn-outline-secondary btn-sm"
                        :disabled="i === sorted.length - 1 || saving"
                        @click="moveDown(i)">↓</button>
              </td>
            </tr>
            <tr v-if="!sorted.length">
              <td colspan="5" class="text-center text-muted">カテゴリがありません</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
table {
  min-width: 720px;
}
code {
  font-size: 0.85em;
  color: #666;
}
</style>
