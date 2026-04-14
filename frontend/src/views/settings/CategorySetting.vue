<!-- CategorySetting.vue - カテゴリ表示順の並び替え -->
<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api'

const cats    = ref([])
const loading = ref(false)
const saving  = ref(false)
const error   = ref('')
const message = ref('')
const showOff = ref(false)  // 非表示(OFF)カテゴリを表示するか

// 全件をグループソート（ON先 → OFF後、各内は sort_order 昇順 → code 昇順）
const sorted = computed(() => {
  return [...cats.value].sort((a, b) => {
    const ag = a.show_in_menu ? 0 : 1
    const bg = b.show_in_menu ? 0 : 1
    if (ag !== bg) return ag - bg
    const ao = Number(a.sort_order ?? 0)
    const bo = Number(b.sort_order ?? 0)
    if (ao !== bo) return ao - bo
    return String(a.code || '').localeCompare(String(b.code || ''))
  })
})

// 表示用（showOff=false なら ON のみ）
const visible = computed(() => {
  if (showOff.value) return sorted.value
  return sorted.value.filter(c => c.show_in_menu)
})

const offCount = computed(() => cats.value.filter(c => !c.show_in_menu).length)

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
  // 現在表示中の visible 上のインデックスで入れ替え、実体の sort_order を更新
  const arr = visible.value
  const target = arr[index]
  const swap   = arr[index + delta]
  if (!target || !swap) return
  // ON/OFF グループ跨ぎの移動は禁止（視覚的な並び崩れ防止）
  if (!!target.show_in_menu !== !!swap.show_in_menu) return

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

// 指定位置で ↑ が無効か（先頭 or 直上がグループ違い）
function cantUp(i) {
  if (i <= 0) return true
  return !!visible.value[i - 1]?.show_in_menu !== !!visible.value[i]?.show_in_menu
}
// 指定位置で ↓ が無効か（末尾 or 直下がグループ違い）
function cantDown(i) {
  if (i >= visible.value.length - 1) return true
  return !!visible.value[i + 1]?.show_in_menu !== !!visible.value[i]?.show_in_menu
}

function moveUp(index)   { move(index, -1) }
function moveDown(index) { move(index, +1) }

async function save() {
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    // 全件を ON→OFF グループ順で送信（OFF非表示時も含めて送る）
    // バックエンドは送られた順に 10, 20, 30... と振り直すので、
    // ON ブロックが常に小さい番号、OFF ブロックが後ろになり、並びが安定する
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
          <button class="btn btn-outline-secondary btn-sm"
                  @click="showOff = !showOff"
                  :disabled="saving">
            {{ showOff ? '非表示を隠す' : `非表示も表示 (${offCount})` }}
          </button>
          <button class="btn btn-outline-secondary btn-sm" @click="reload" :disabled="saving">再読込</button>
          <button class="btn btn-primary btn-sm" @click="save" :disabled="saving">
            {{ saving ? '保存中…' : '並び順を保存' }}
          </button>
        </div>
      </div>

      <p class="small text-muted mb-3">
        注文画面などのカテゴリ表示順を変更できます。<br>
        <strong>この並び順はこの店舗専用です。</strong>他店舗には影響しません。<br>
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
            <tr v-for="(c, i) in visible"
                :key="c.code"
                :class="{ 'table-off-row': !c.show_in_menu }">
              <td class="text-muted">{{ c.show_in_menu ? (i + 1) : '-' }}</td>
              <td>{{ c.name }}</td>
              <td><code>{{ c.code }}</code></td>
              <td>
                <span v-if="c.show_in_menu" class="badge bg-success">ON</span>
                <span v-else class="badge bg-secondary">OFF</span>
              </td>
              <td>
                <button class="btn btn-outline-secondary btn-sm me-1"
                        :disabled="cantUp(i) || saving"
                        @click="moveUp(i)">↑</button>
                <button class="btn btn-outline-secondary btn-sm"
                        :disabled="cantDown(i) || saving"
                        @click="moveDown(i)">↓</button>
              </td>
            </tr>
            <tr v-if="!visible.length">
              <td colspan="5" class="text-center text-muted">
                {{ cats.length ? '表示中のカテゴリがありません（「非表示も表示」で全件見えます）' : 'カテゴリがありません' }}
              </td>
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
.table-off-row {
  background-color: #f8f9fa;
  color: #888;
}
</style>
