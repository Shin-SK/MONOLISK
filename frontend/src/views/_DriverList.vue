<script setup>
import { ref, onMounted, watch } from 'vue'
import { api } from '@/api'

/* ---------- 状態 ---------- */
const rows      = ref([])
const date      = ref('')                       // '' = 全件
const loading   = ref(false)

/* 今日の日付 YYYY-MM-DD */
function todayStr () {
  return new Date().toISOString().slice(0, 10)
}

/* ---------- API ---------- */
async function fetchRows () {
  loading.value = true
  const params  = date.value ? { date: date.value } : {}
  const { data } = await api.get('reservations/mine-driver/', { params })
  /* 新しい順（開始日時 DESC）で並べ替え */
  rows.value = data.sort((a, b) => new Date(b.start_at) - new Date(a.start_at))
  loading.value = false
}

/* 初回 & date 変更で再取得 */
onMounted(fetchRows)
watch(date, fetchRows)
</script>

<template>
  <div class="container py-4">
    <h1 class="h4 mb-3">
      担当予約一覧
    </h1>

    <!-- フィルター -->
    <div class="d-flex align-items-center gap-2 mb-3">
      <input
        v-model="date"
        type="date"
        class="form-control"
        style="max-width:180px"
      >
      <button
        class="btn btn-outline-secondary"
        @click="date = ''"
      >
        全件
      </button>
      <button
        class="btn btn-primary"
        @click="date = todayStr()"
      >
        今日
      </button>
    </div>

    <!-- テーブル -->
    <table
      v-if="rows.length"
      class="table table-sm"
    >
      <thead>
        <tr>
          <th>開始</th><th>キャスト</th><th>顧客</th><th>見積</th><th />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in rows"
          :key="r.id"
        >
          <td>{{ new Date(r.start_at).toLocaleString() }}</td>
          <td>{{ r.cast_names.join(', ') }}</td>
          <td>{{ r.customer_name }}</td>
          <td class="text-end">
            {{ r.expected_amount.toLocaleString() }} 円
          </td>
          <td class="text-end">
            <RouterLink
              :to="{ name:'reservation-detail', params:{ id:r.id } }"
              class="btn btn-sm btn-outline-primary"
            >
              詳細
            </RouterLink>
          </td>
        </tr>
      </tbody>
    </table>

    <p
      v-else
      v-if="!loading"
      class="text-muted"
    >
      データがありません
    </p>
    <p v-if="loading">
      読み込み中...
    </p>
  </div>
</template>
