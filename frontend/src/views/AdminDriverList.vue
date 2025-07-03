<!-- src/views/AdminDriverList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api'                // drivers, stores 共通

const keyword = ref('')
const store   = ref('')
const stores  = ref([])
const results = ref([])

/* ───────── マスタ取得 ───────── */
async function fetchStores () {
  stores.value = await api.get('stores/').then(r => r.data)
  store.value  = stores.value[0]?.id ?? ''
}

/* ───────── 一覧取得 ───────── */
async function fetch () {
  const { data: drivers } = await api.get('drivers/', {
    params: { store: store.value, search: keyword.value }
  })

  /* 必要に応じて追加データをマージするならここで */
  results.value = drivers
}

onMounted(async () => {
  await fetchStores()
  await fetch()
})
</script>

<template>
<div class="container-fluid py-4">
  <h1 class="h4 mb-3 text-center">ドライバー一覧</h1>

  <div class="d-flex gap-2 mb-3">
    <select v-model="store" @change="fetch" class="form-select" style="max-width:200px">
      <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
    </select>
    <input v-model="keyword" @keyup.enter="fetch" class="form-control" placeholder="名前・電話を検索" style="max-width:200px">
    <RouterLink to="/drivers/new" class="btn btn-primary">＋登録</RouterLink>
  </div>

  <table class="table table-sm">
    <thead>
      <tr><th>ID</th><th>ユーザー</th><th>電話</th><th>車種</th><th>ナンバー</th><th>編集</th></tr>
    </thead>
    <tbody>
      <tr v-for="d in results" :key="d.id">
        <td>{{ d.id }}</td>
        <td>{{ d.name }}</td>
        <td>{{ d.phone || '―' }}</td>
        <td>{{ d.car_type || '―' }}</td>
		<td>{{ d.number || '―' }}</td>
        <td>
          <RouterLink :to="`/drivers/${d.id}`" class="btn btn-sm btn-outline-secondary">編集</RouterLink>
        </td>
      </tr>
    </tbody>
  </table>
</div>
</template>
