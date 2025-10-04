<!-- src/views/CastList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import Avatar from '@/components/Avatar.vue'
import { getBillingCasts, fetchCastShifts } from '@/api'

const keyword = ref('')
const results = ref([])

const fmt = (iso) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''

async function fetchList () {
  // 1) キャスト一覧（所属店舗は X-Store-Id によりサーバ側で絞られる）
  const casts = await getBillingCasts(
    { stage_name: keyword.value || undefined, _ts: Date.now() },
    { cache: false }
  )

  // 2) 今日のシフト（店舗は送らない）
  const today  = new Date().toISOString().slice(0, 10)
  const shifts = await fetchCastShifts({ date: today })
  const byCast = Object.fromEntries((Array.isArray(shifts) ? shifts : []).map(s => [s.cast_id, s]))

  // 3) 表示用整形
  results.value = (Array.isArray(casts) ? casts : []).map(c => {
    const sh = byCast[c.id]
    return {
      ...c,
      shiftLabel: sh ? `${fmt(sh.plan_start)}-${fmt(sh.plan_end)}` : '—',
    }
  })
}

onMounted(fetchList)
</script>

<template>
  <div class="py-4">
    <div class="d-flex gap-2 mb-5 flex-wrap">
      <input
        v-model="keyword"
        class="form-control"
        placeholder="源氏名で検索（Enterで実行）"
        @keyup.enter="fetchList"
      >
      <RouterLink
        :to="{ name: 'settings-cast-new' }"
        class="d-flex align-items-center btn btn-primary ms-auto"
      >新規登録</RouterLink>
    </div>

    <table class="table">
      <thead class="table-dark">
        <tr>
          <th>ID</th>
          <th>源氏名</th>
          <th>本日の予定</th>
          <th class="text-end">編集</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in results" :key="c.id">
          <td style="vertical-align:middle;">{{ c.id }}</td>
          <td style="vertical-align:middle;">
            <div class="d-flex align-items-center gap-1">
              <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="28" />
              <span>{{ c.stage_name }}</span>
            </div>
          </td>
          <td style="vertical-align:middle;">{{ c.shiftLabel }}</td>
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
input{
  background-color: white;
}
</style>
