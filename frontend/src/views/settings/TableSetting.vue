<script setup>
import { ref, onMounted } from 'vue'
import { api, getStores, fetchTables } from '@/api'

const stores = ref([])
const storeId = ref(null)

const rows = ref([])
const loading = ref(false)
const error   = ref('')

const newNumber = ref('')

async function load() {
  error.value = ''
  loading.value = true
  try {
    stores.value = await getStores()
    storeId.value = stores.value[0]?.id ?? null
    if (!storeId.value) return
    const data = await fetchTables(storeId.value)
    rows.value = Array.isArray(data?.results) ? data.results : data
  } catch (e) {
    error.value = e?.response?.data?.detail || '読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

async function add() {
  if (!newNumber.value) return
  try {
    const res = await api.post('billing/tables/', { number: +newNumber.value })
    rows.value.push(res.data)
    newNumber.value = ''
  } catch (e) {
    alert(e?.response?.data?.detail || '追加に失敗しました（重複している可能性）')
  }
}

async function remove(row) {
  if (!confirm(`テーブル T${row.number} を削除しますか？`)) return
  try {
    await api.delete(`billing/tables/${row.id}/`)
    rows.value = rows.value.filter(r => r.id !== row.id)
  } catch (e) {
    alert(e?.response?.data?.detail || '削除に失敗しました')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="d-flex align-items-end gap-2 mb-3">
      <div>
        <label class="form-label small mb-1">新規テーブル番号</label>
        <input type="number" class="form-control bg-white" v-model="newNumber" placeholder="例: 1" style="max-width:160px" />
      </div>
      <button class="btn btn-primary" @click="add">追加</button>
    </div>

    <div v-if="loading" class="text-muted">読み込み中…</div>

    <div v-else class="table-responsive">
      <table class="table table-sm align-middle">
        <thead class="table-light">
          <tr>
            <th style="width:20%">ID</th>
            <th>テーブル番号</th>
            <th style="width:15%"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>T{{ r.number }}</td>
            <td class="text-end">
              <button class="btn btn-outline-danger btn-sm" @click="remove(r)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
  </div>
</template>


<style scoped lang="scss">

table{
  td,th{
    white-space: nowrap;
  }
}

</style>