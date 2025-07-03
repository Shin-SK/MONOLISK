<script setup>
import { ref, onMounted } from 'vue'
import { api, getShiftPlans } from '@/api'   // ★追加


const keyword  = ref('')
const store    = ref('')
const stores   = ref([])
const results  = ref([])

async function fetchStores() {
  stores.value = await api.get('stores/').then(r => r.data)
  store.value  = stores.value[0]?.id ?? ''
}
async function fetch() {
	/* 1) キャスト一覧 */
	const { data: casts } = await api.get('cast-profiles/', {
	  params:{ store:store.value, stage_name:keyword.value }
	})

	/* 2) 今日の出勤予定（同店舗に絞る） */
	const today   = new Date().toISOString().slice(0,10)
	const shifts  = await getShiftPlans({ store:store.value, date: today })
	const byCast  = Object.fromEntries(shifts.map(s => [s.cast_profile, s]))

	/* 3) マージしてテーブル描画用へ */
	results.value = casts.map(c => ({
	  ...c,
	  shift: byCast[c.id] ? `${byCast[c.id].start_at}-${byCast[c.id].end_at}` : '―'
	}))
}

onMounted(async () => {
  await fetchStores()
  await fetch()
})
</script>

<template>
<div class="container-fluid py-4">
  <h1 class="h4 mb-3">キャスト一覧</h1>

  <div class="d-flex gap-2 mb-3">
    <select v-model="store" @change="fetch" class="form-select" style="max-width:200px">
      <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
    </select>
    <input v-model="keyword" @keyup.enter="fetch" class="form-control" placeholder="源氏名">
    <RouterLink to="/casts/new" class="btn btn-primary">＋ 登録</RouterLink>
  </div>

  <table class="table table-sm">
  <thead><tr><th>ID</th><th>源氏名</th><th>Rank</th><th>☆</th><th>本日シフト</th><th>編集</th></tr></thead>
    <tbody>
      <tr v-for="c in results" :key="c.id">
        <td>{{ c.id }}</td>
        <td>{{ c.stage_name }}</td>
        <td>{{ c.rank }}</td>
        <td>{{ c.star_count }}</td>
        <td>{{ c.shift }}</td>
        <td>
          <RouterLink :to="`/casts/${c.id}`" class="btn btn-sm btn-outline-secondary">編集</RouterLink>
        </td>
      </tr>
    </tbody>
  </table>
</div>
</template>
