<!-- src/views/CustomerList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import { searchCustomers, createCustomer } from '@/api'

const keyword = ref('')
const results = ref([])
const loading = ref(false)

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
    }))
  } finally {
    loading.value = false
  }
}

onMounted(fetchList)

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
  <div class="customer customer-list py-4">
    <!-- 検索バー -->
    <div class="input-group mb-3">
      <input
        v-model="keyword"
        class="form-control bg-white"
        placeholder="名前 または 電話番号"
        @keyup.enter="fetchList"
      />
      <button class="btn btn-outline-secondary bg-white" @click="fetchList">検索</button>
      <button class="btn btn-primary" @click="addCustomer">＋ 登録</button>
    </div>

    <div v-if="results.length" class="table-responsive">
      <!-- 一覧 -->
      <table class="table table-bordered table-hover align-middle table-striped">
        <thead>
          <tr>
            <th>ID</th>
            <th>名前</th>
            <th>あだ名</th>
            <th>電話</th>
            <th>誕生日</th>
            <th class="memo">メモ</th>
            <th class="text-end">編集</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in results" :key="c.id">
            <td>{{ c.id }}</td>
            <td>{{ (c.alias?.trim() || c.full_name?.trim()) || '-' }}</td>
            <td>{{ c.alias || '-' }}</td>
            <td>{{ c.phone || '-' }}</td>
            <td>{{ fmtBirthday(c.birthday) }}</td>
            <td class="memo">{{ c.memo || '-' }}</td>
            <td class="text-end">
              <RouterLink
                :to="{ name: 'customer-detail', params: { id: c.id } }"
                class="btn btn-sm btn-outline-secondary"
              >
                編集
              </RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
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
  white-space: pre-line;        /* 改行文字を活かしつつ通常折り返しも可 */
  overflow-wrap: anywhere;      /* スペース無しの長文/URLも折返し */
  word-break: break-word;       /* 旧ブラウザ対策 */
  min-width: 240px;             /* ★ ここが肝：列が潰れない最低幅 */
  vertical-align: top;          /* 行高が増えても見やすく */
}
</style>
