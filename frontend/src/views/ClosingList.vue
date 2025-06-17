<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/api'

const date  = ref(new Date().toISOString().slice(0,10))
const store = ref('')
const stores = ref([])
const rows  = ref([])

async function fetchStores() {
  stores.value = await api.get('stores/').then(r=>r.data)
  store.value = stores.value[0]?.id ?? ''
}
async function fetch() {
  const { data } = await api.get('reservations/', {
    params:{ date: date.value, store: store.value }
  })
  rows.value = data
}
onMounted(async () => {
  await fetchStores()
  await fetch()
})
</script>

<template>
<div class="container py-4">
  <h1 class="h4 mb-3">日次精算</h1>

  <div class="d-flex gap-2 mb-3">
    <input type="date" v-model="date" @change="fetch" class="form-control" style="max-width:180px">
    <select v-model="store" @change="fetch" class="form-select" style="max-width:200px">
      <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
    </select>
  </div>

  <table class="table table-sm">
    <thead>
      <tr><th>開始</th><th>キャスト</th><th>顧客</th>
          <th class="text-end">見積</th><th class="text-end">受取</th><th class="text-end">差額</th></tr>
    </thead>
    <tbody>
      <tr v-for="r in rows" :key="r.id"
          :class="{'table-danger': r.discrepancy_flag}">
        <td>{{ new Date(r.start_at).toLocaleTimeString() }}</td>
        <td>{{ r.cast_names.join(', ') }}</td>
        <td>{{ r.customer_name }}</td>
        <td class="text-end">{{ r.expected_amount.toLocaleString() }}</td>
        <td class="text-end">{{ (r.received_amount ?? 0).toLocaleString() }}</td>
        <td class="text-end">
          {{ ((r.received_amount ?? 0) - r.expected_amount).toLocaleString() }}
        </td>
      </tr>
    </tbody>
  </table>
</div>
</template>
