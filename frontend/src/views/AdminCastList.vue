<!-- src/views/CastList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { api, getShiftPlans } from '@/api'

const keyword	= ref('')
const store		= ref('')
const stores	= ref([])
const results	= ref([])

async function fetchStores() {
	const list = await api.get('billing/stores/').then(r => r.data)
	stores.value = [{ id: '', name: '全店舗' }, ...list]
	store.value  = ''
}

async function fetch() {
	/* 1) キャスト一覧（Billing） */
	const { data: casts } = await api.get('billing/casts/', {
		params: {
			store      : store.value || undefined,
			stage_name : keyword.value
		}
	})

	/* 2) 今日の出勤予定（旧 core エンドポイントを暫定利用） */
	const today  = new Date().toISOString().slice(0, 10)
	const shifts = await getShiftPlans({
		store: store.value || undefined,
		date : today
	})
	const byCast = Object.fromEntries(shifts.map(s => [s.cast_profile, s]))

	/* 3) マージして表示用データに変換 */
	results.value = casts.map(c => ({
		...c,
		shift: byCast[c.id]
			? `${byCast[c.id].start_at}-${byCast[c.id].end_at}`
			: '―'
	}))
}

onMounted(async () => {
	await fetchStores()
	await fetch()
})
</script>

<template>
  <div class="container-fluid py-4">
    <div class="d-flex gap-2 mb-5">
      <select
        v-model="store"
        class="form-select"
        style="max-width:200px"
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
        class="form-control h-auto w-25"
        placeholder="源氏名"
        @keyup.enter="fetch"
      >
      <RouterLink
        to="/casts/new"
        class="d-flex align-items-center btn btn-primary ms-auto"
      >
        新規登録
      </RouterLink>
    </div>

    <table class="table">
      <thead class="table-dark">
        <tr><th>ID</th><th>源氏名</th><th>編集</th></tr>
      </thead>
      <tbody>
        <tr
          v-for="c in results"
          :key="c.id"
        >
          <td>{{ c.id }}</td>
          <td>{{ c.stage_name }}</td>
          <td class="text-end p-2">
            <RouterLink
              :to="`/casts/${c.id}`"
              class="btn  btn-outline-secondary"
            >
              編集
            </RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
