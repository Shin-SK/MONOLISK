<!-- src/views/AdminStaffList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import { fetchStaffs, fetchStaffShifts } from '@/api'

const keyword = ref('')
const results = ref([])

/* ---------- util ---------- */
const ensureShift = async (row) => {
  if (!row.shift) {
    row.shift = await createStaffShift({
      staff_id : row.id,
      store_id : row.stores[0] ?? getStoreId(),
    })
  }
}

/* ---------- 操作 ---------- */
async function checkIn (row) {
  await ensureShift(row)
  if (!row.shift.clock_in) {
    await staffCheckIn(row.shift.id)
    fetchList()
  }
}

async function checkOut (row) {
  if (row.shift && !row.shift.clock_out) {
    if (!confirm('退勤しますか？')) return
    await staffCheckOut(row.shift.id)
    alert('退勤処理が完了しました！')
    fetchList()     // 退勤済み行は条件から外れる
  }
}

async function removeShift (row) {
  if (row.shift && confirm('本当に削除しますか？')) {
    await deleteStaffShift(row.shift.id)
    fetchList()
  }
}


async function fetchList () {
  /* ① スタッフ一覧 */
  const staffs = await fetchStaffs({ name: keyword.value })

  /* ② 今日のシフト取得 */
  const today   = dayjs().format('YYYY-MM-DD')
  const shifts  = await fetchStaffShifts({ date: today })
  const byStaff = Object.fromEntries(shifts.map(s => [s.staff_id, s]))

  /* ③ マージして表示用配列生成 */
  results.value = staffs.map(s => {
    const sh = byStaff[s.id]
    return {
      ...s,
      name : s.full_name || s.username,  
      shift: sh
        ? `${dayjs(sh.plan_start).format('YYYY/MM/DD HH:mm')}-${dayjs(sh.plan_end).format('HH:mm')}`
        : '—'               // シフト無し
    }
  })
}

onMounted(fetchList)
</script>


<template>
  <div class="container-fluid py-4 staff-list">
    <!-- 検索フォーム -->
    <div class="d-flex gap-2 mb-5">
      <input
        v-model="keyword"
        class="form-control w-25"
        placeholder="スタッフ名"
        @keyup.enter="fetchList"
      >
      <RouterLink
        to="/staffs/new"
        class="btn btn-primary ms-auto d-flex align-items-center"
      >
        新規登録
      </RouterLink>
    </div>

    <!-- 一覧テーブル -->
    <table class="table align-middle">
      <thead class="table-dark">
        <tr>
          <th>ID</th>
          <th>氏名</th>
          <th>役職</th>
          <th>今日のシフト</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="s in results"
          :key="s.id"
        >
          <td>{{ s.id }}</td>
          <td>
            <RouterLink :to="`/staff/${s.id}`">
              {{ s.name }}
            </RouterLink>
          </td>
          <td>{{ s.role_label || '―' }}</td>
          <td>{{ s.shift }}</td>
          <!-- ★操作列を追加 -->
          <td class="text-end p-2">
            <!-- 出勤 -->
            <button
              v-if="!s.shift?.clock_in"
              class="btn btn-outline-primary"
              @click="checkIn(s)"
            >
              出勤
            </button>

            <!-- 退勤 -->
            <button
              v-else-if="!s.shift?.clock_out"
              class="btn btn-outline-success"
              @click="checkOut(s)"
            >
              退勤
            </button>

            <!-- 削除 -->
            <button
              v-else
              class="btn btn-outline-secondary"
              @click="removeShift(s)"
            >
              削除
            </button>
          </td>
        </tr>

        <!-- データ無し -->
        <tr v-if="!results.length">
          <td
            colspan="5"
            class="text-center text-muted"
          >
            スタッフがいません
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
