<!-- src/views/AdminStaffList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { fetchStaffs, getStaffShiftPlans } from '@/api'
import dayjs from 'dayjs'

/* ---------- reactive state ---------- */
const keyword  = ref('')
const results  = ref([])

/* ---------- fetch ---------- */
async function fetchList () {
  // ① スタッフ本体
  const staffs = await fetchStaffs({ name: keyword.value })

  // ② 今日の予定
  const today   = dayjs().format('YYYY-MM-DD')
  const shifts  = await getStaffShiftPlans({ date: today })
  const byStaff = Object.fromEntries(shifts.map(s => [s.staff_id, s]))

  // ③ マージ
  results.value = staffs.map(s => ({
    ...s,
    shift: byStaff[s.id]
      ? `${byStaff[s.id].start_at}-${byStaff[s.id].end_at}`
      : '―'
  }))
}

/* ---------- mount ---------- */
onMounted(fetchList)
</script>

<template>
  <div class="container-fluid py-4 staff-list">
    <!-- 検索フォーム -->
    <div class="d-flex gap-2 mb-3">
      <input v-model="keyword" @keyup.enter="fetchList"
             class="form-control w-50" placeholder="スタッフ名">
      <RouterLink to="/staffs/new"
                  class="btn btn-primary ms-auto d-flex align-items-center">
        ＋ 登録
      </RouterLink>
    </div>

    <!-- 一覧テーブル -->
    <table class="table table-sm align-middle">
      <thead class="table-light">
        <tr>
          <th>ID</th>
          <th>氏名</th>
          <th>役職</th>
          <th>今日のシフト</th>
          <th>編集</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in results" :key="s.id">
          <td>{{ s.id }}</td>
          <td>{{ s.name }}</td>
          <td>{{ s.role || '―' }}</td>
          <td>{{ s.shift }}</td>
          <td>
            <RouterLink :to="`/staffs/${s.id}`"
                        class="btn btn-sm btn-outline-secondary">
              編集
            </RouterLink>
          </td>
        </tr>

        <!-- データ無し -->
        <tr v-if="!results.length">
          <td colspan="5" class="text-center text-muted">スタッフがいません</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
