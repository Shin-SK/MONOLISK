<!-- src/views/CustomerList.vue -->
<script setup>
import { ref, onMounted, computed, watch } from 'vue'
const props = defineProps({
  reloadTs: { type: Number, default: 0 },
  lastSaved: { type: Object, default: null },
})
import dayjs from 'dayjs'
import { searchCustomers, createCustomer } from '@/api'

const keyword = ref('')
const results = ref([])
const loading = ref(false)
const includeEmpty = ref(false)

const fmtBirthday = d =>
  d ? dayjs(d).format('YYYY/MM/DD') : '-'

async function fetchList () {
  loading.value = true
  try {
    const list = await searchCustomers(keyword.value)
    // 念のためキーを揃える
    results.value = (Array.isArray(list) ? list : []).map(c => ({
      id: c.id,
      full_name: c.full_name ?? '',
      alias: c.alias ?? '',
      phone: c.phone ?? '',
      birthday: c.birthday ?? null,
      memo: c.memo ?? '',
      tags: Array.isArray(c.tags) ? c.tags : [],
      last_visit_at: c.last_visit_at ?? c.last_visit ?? null,
      last_cast_obj: c.last_cast_obj ?? null,
      has_bottle: c.has_bottle ?? false,
      bottle_shelf: c.bottle_shelf ?? '',
      bottle_memo: c.bottle_memo ?? '',
    }))
  } finally {
    loading.value = false
  }
}

onMounted(fetchList)

// 親からの再取得トリガー
watch(() => props.reloadTs, (ts) => {
  if (ts) fetchList()
})

// 直近保存顧客をローカル一覧に反映
watch(() => props.lastSaved, (cust) => {
  if (!cust || typeof cust !== 'object') return
  const idx = results.value.findIndex(c => c.id === cust.id)
  const normalized = {
    id: cust.id,
    full_name: cust.full_name ?? '',
    alias: cust.alias ?? '',
    phone: cust.phone ?? '',
    birthday: cust.birthday ?? null,
    memo: cust.memo ?? '',
    tags: Array.isArray(cust.tags) ? cust.tags : (Array.isArray(cust.tag_ids) ? (cust.tag_ids.map(id => ({ id, name: '' }))) : []),
    last_visit_at: cust.last_visit_at ?? cust.last_visit ?? null,
    last_cast_obj: cust.last_cast_obj ?? null,
    has_bottle: cust.has_bottle ?? false,
    bottle_shelf: cust.bottle_shelf ?? '',
    bottle_memo: cust.bottle_memo ?? '',
  }
  if (idx >= 0) {
    results.value[idx] = normalized
  } else {
    results.value.unshift(normalized)
  }
}, { deep: false })

const filteredResults = computed(() => {
  if (includeEmpty.value) return results.value
  return results.value.filter(c => (c.alias?.trim() || c.full_name?.trim()) )
})

/* ---------- 新規登録（超簡易） ---------- */
async function addCustomer () {
  const name  = prompt('顧客名');     if (!name)  return
  const phone = prompt('電話番号');   if (!phone) return
  const memo  = prompt('メモ') || ''

  await createCustomer({ name, phone, memo })
  alert('登録しました')
  // サーバ正規化後の値で再取得
  await fetchList()
}
</script>

<template>
  <div class="customer customer-list">
    <!-- 検索バー -->
    <div class="row g-2 mb-3 align-items-center">
      <div class="col-12">
        <input
          v-model="keyword"
          class="form-control bg-white"
          placeholder="名前 または 電話番号"
          @keyup.enter="fetchList"
        />
      </div>
      <div class="col-6">
        <div class="form-check form-switch m-0 toggle">
          <input
            class="form-check-input"
            type="checkbox"
            id="includeEmptySwitch"
            v-model="includeEmpty"
          >
          <label class="form-check-label small" for="includeEmptySwitch">未入力も含む</label>
        </div>
      </div>
      <div class="col-3">
        <button class="btn btn-sm btn-outline-secondary bg-white w-100 h-100" @click="fetchList">検索</button>
      </div>
      <div class="col-3">
      <button class="btn btn-sm btn-primary w-100 h-100" @click="addCustomer">登録</button>
      </div>
    </div>

    <div v-if="filteredResults.length">
      <div v-for="c in filteredResults" :key="c.id" class="card mb-3">
        <div class="card-header d-flex align-items-center justify-content-between gap-2">
          <div class="d-flex align-items-center gap-1 flex-wrap fw-bold">
            <span v-if="c.alias" class="me-1">{{ c.alias || '-' }} /</span>
            <span>{{ c.full_name?.trim() || '-' }} 様</span>
          </div>
          <RouterLink
            :to="{ name: 'customer-detail', params: { id: c.id } }"
            class="btn btn-sm"
          >
            <IconPencil />
          </RouterLink>
        </div>
        <div class="card-body border-bottom">
          <div class="row g-2">
            <div class="col-6 d-flex flex-column align-items-center gap-1">
              <div class="badge bg-light text-dark">電話番号</div>
              <div>{{ c.phone || '-' }}</div>
            </div>
            <div class="col-6 d-flex flex-column align-items-center gap-1">
              <div class="badge bg-light text-dark">誕生日</div>
              <div>{{ fmtBirthday(c.birthday) }}</div>
            </div>
            <div class="col-6 d-flex flex-column align-items-center gap-1">
              <div class="badge bg-light text-dark">最終来店日</div>
              <div>{{ c.last_visit_at ? dayjs(c.last_visit_at).format('YYYY/MM/DD HH:mm') : '-' }}</div>
            </div>
            <div class="col-6 d-flex flex-column align-items-center gap-1">
              <div class="badge bg-light text-dark">最終担当</div>
              <div class="badge bg-secondary text-white">{{ c.last_cast_obj?.stage_name || '-' }}</div>
            </div>
            <div class="col-12 row align-items-center mt-3">
              <div class="col-2 d-flex px-1">
                <span class="badge bg-light text-dark">タグ</span>
              </div>
              <div class="col-10">
                <div v-if="c.tags?.length" class="d-flex flex-wrap gap-1 align-items-center">
                  <span
                    v-for="tag in c.tags"
                    :key="tag.id"
                  >
                    {{ tag.name }},
                  </span>
                </div>
                <span v-else class="text-muted">-</span>
              </div>
            </div>
            <div v-if="c.has_bottle" class="col-12 mt-3">
              <div class="card bg-light">
                <div class="card-body p-2">
                  <div class="d-flex align-items-center gap-2 mb-1">
                    <span class="badge bg-success">🍾 マイボトル</span>
                    <span v-if="c.bottle_shelf" class="badge bg-secondary">{{ c.bottle_shelf }}</span>
                  </div>
                  <div v-if="c.bottle_memo" class="small text-muted">{{ c.bottle_memo }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="card-footer">
          <span class="badge bg-light text-dark mb-2">メモ</span>
          <div class="memo">{{ c.memo || '-' }}</div>
        </div>
      </div>
    </div>
    <p v-else-if="!loading" class="text-muted">結果がありません</p>
    <p v-else>読み込み中...</p>
  </div>
</template>

<style scoped lang="scss">
table{
  td,th{
    white-space: nowrap;
  }
}
.memo { 
  white-space: pre-line; 
  overflow-wrap: anywhere;      /* スペース無しの長文/URLも折返し */
  word-break: break-word;       /* 旧ブラウザ対策 */
  min-width: 240px;             /* ★ ここが肝：列が潰れない最低幅 */
  vertical-align: top;          /* 行高が増えても見やすく */
}

/* トグルスイッチを少し大きく見せる */
.toggle-large .form-check-input {
  width: 3.2rem;
  height: 1.8rem;
  cursor: pointer;
}
.toggle-large .form-check-input:checked {
  background-color: #0d6efd; /* Bootstrap primary */
  border-color: #0d6efd;
}
.toggle-large .form-check-label {
  margin-left: .5rem;
  line-height: 1.8rem;
  cursor: pointer;
}
</style>
