<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import {
  fetchStaffs, fetchStaffShifts,
  createStaffShift, deleteStaffShift,
  staffCheckIn, staffCheckOut,
} from '@/api'
import { getStoreId } from '@/auth'

const keyword = ref('')
const results = ref([])

const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '—'

// ▼ 表示用フォールバック
const displayName = (s) => {
  // 1) full_name があれば最優先
  if (s.full_name && String(s.full_name).trim()) return s.full_name
  // 2) first_name + last_name
  const fn = [s.first_name, s.last_name].filter(Boolean).join('')
  if (fn) return fn
  // 3) username or name（バックエンド差異吸収）
  if (s.username && String(s.username).trim()) return s.username
  if (s.name && String(s.name).trim()) return s.name
  // 4) 最終フォールバック
  return `ID:${s.id}`
}

const displayRole = (s) => {
  // role_label が来ていればそれでOK
  if (s.role_label && String(s.role_label).trim()) return s.role_label
  // role_code から人間表示へ
  const map = { staff: 'スタッフ', submgr: '副店長', mgr: '店長' }
  if (s.role_code && map[s.role_code]) return map[s.role_code]
  // 何も無ければダッシュ
  return '―'
}

async function ensureShift (row) {
  if (!row.shift) {
    row.shift = await createStaffShift({
      staff_id : row.id,
      store_id : row.stores?.[0] ?? getStoreId(),
    })
  }
}

async function checkIn (row) {
  await ensureShift(row)
  if (!row.shift?.clock_in) {
    await staffCheckIn(row.shift.id)
    await fetchList()
  }
}

async function checkOut (row) {
  if (row.shift && !row.shift.clock_out) {
    if (!confirm('退勤しますか？')) return
    await staffCheckOut(row.shift.id)
    alert('退勤処理が完了しました！')
    await fetchList()
  }
}

async function removeShift (row) {
  if (row.shift && confirm('本当に削除しますか？')) {
    await deleteStaffShift(row.shift.id)
    await fetchList()
  }
}

async function fetchList () {
  // ※ バックエンド側の検索キーが不明なら { q: keyword.value } にする手も
  const staffs = await fetchStaffs({ name: keyword.value })
  const today   = dayjs().format('YYYY-MM-DD')
  const shifts  = await fetchStaffShifts({ date: today })
  const byStaff = Object.fromEntries((Array.isArray(shifts)?shifts:[]).map(s => [s.staff_id, s]))

  results.value = (Array.isArray(staffs)?staffs:[]).map(s => {
    const sh = byStaff[s.id] || null
    return {
      ...s,
      _name: displayName(s),            // ← ここに確実な表示名
      _role: displayRole(s),            // ← ここに確実な役職表示
      shift: sh,
      shiftLabel: sh
        ? `${fmt(sh.plan_start)}-${(sh.plan_end && dayjs(sh.plan_end).format('HH:mm')) || '—'}`
        : '—',
    }
  })
}

onMounted(fetchList)
</script>

<template>
  <div class="container-fluid py-4 staff-list">
    <div class="d-flex gap-2 mb-5">
      <input
        v-model="keyword"
        class="form-control w-25 bg-white"
        placeholder="スタッフ名"
        @keyup.enter="fetchList"
      >
      <RouterLink :to="{ name: 'settings-staff-new' }" class="btn btn-primary ms-auto">
        新規登録
      </RouterLink>
    </div>

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
        <tr v-for="s in results" :key="s.id">
          <td>{{ s.id }}</td>
          <td>
            <RouterLink :to="{ name: 'settings-staff-form', params: { id: s.id } }">
              {{ s._name }}
            </RouterLink>
          </td>
          <td>{{ s._role }}</td>
          <td>{{ s.shiftLabel }}</td>
          <td class="text-end p-2">
            <button class="btn btn-secondary" v-if="!s.shift?.clock_in" @click="checkIn(s)">出勤</button>
            <button class="btn btn-secondary" v-else-if="!s.shift?.clock_out" @click="checkOut(s)">退勤</button>
            <button
              v-else
              class="btn btn-outline-secondary"
              @click="removeShift(s)"
            >
              削除
            </button>
          </td>
        </tr>

        <tr v-if="!results.length">
          <td colspan="5" class="text-center text-muted">スタッフがいません</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
