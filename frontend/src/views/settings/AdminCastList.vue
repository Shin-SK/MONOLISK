<!-- src/views/CastList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { api, fetchCastShifts } from '@/api'

const keyword	= ref('')
const store		= ref('')
const stores	= ref([])
const results	= ref([])

async function fetchStores() {
	const list = await api.get('billing/stores/').then(r => r.data)
	stores.value = [{ id: '', name: '全店舗' }, ...list]
	store.value  = ''
}

const fmt = iso => iso ? new Date(iso).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' }) : ''

async function fetch() {
  // 1) キャスト一覧
  const { data: casts } = await api.get('billing/casts/', {
    params: {
      store      : store.value || undefined,
      stage_name : keyword.value || undefined,
    }
  })

  // 2) 今日のシフト（cast-shifts を日付絞り）
  const today  = new Date().toISOString().slice(0, 10)
  const shifts = await fetchCastShifts({
    date : today,
    store: store.value || undefined,
  })
  const byCast = Object.fromEntries(shifts.map(s => [s.cast_id, s]))

  // 3) 表示用
  results.value = casts.map(c => {
    const sh = byCast[c.id]
    return {
      ...c,
      shiftLabel: sh ? `${fmt(sh.plan_start)}-${fmt(sh.plan_end)}` : '—',
    }
  })
}

onMounted(async () => {
	await fetchStores()
	await fetch()
})
</script>

<template>
  <div class="py-4">
    <div class="d-flex gap-2 mb-5 flex-wrap">
      <select
        v-model="store"
        class="form-select form-control"
        @change="fetch"
      >
        <option
          v-for="s in stores"
          :key="s.id"
          :value="s.id"
        >
          {{ s.name }}
        </option>
      </select>
      <input
        v-model="keyword"
        class="form-control"
        placeholder="源氏名"
        @keyup.enter="fetch"
      >
      <RouterLink
        :to="{ name: 'settings-cast-new' }"
        class="d-flex align-items-center btn btn-primary ms-auto"
      >新規登録</RouterLink>
    </div>

    <table class="table">
      <thead class="table-dark">
        <tr><th>ID</th><th>源氏名</th><th class="text-end">編集</th></tr>
      </thead>
      <tbody>
        <tr
          v-for="c in results"
          :key="c.id"
        >
          <td style="vertical-align:middle;">{{ c.id }}</td>
          <td style="vertical-align:middle;">{{ c.stage_name }}</td>
          <td class="text-end p-2">
            <RouterLink
              :to="{ name:'settings-cast-form', params:{ id:c.id }}"
              class="btn btn-outline-secondary"
            >編集</RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>

input,select{
  background-color: white;
}


</style>