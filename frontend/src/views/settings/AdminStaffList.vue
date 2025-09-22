<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import { fetchStaffs, fetchStaffShifts } from '@/api'

const keyword = ref('')
const results = ref([])

const fmt = d => (d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '—')

const displayName = (s) => {
  if (s.full_name?.trim()) return s.full_name
  const fn = [s.first_name, s.last_name].filter(Boolean).join('')
  if (fn) return fn
  if (s.username?.trim()) return s.username
  if (s.name?.trim()) return s.name
  return `ID:${s.id}`
}
const displayRole = (s) => {
  if (s.role_label?.trim()) return s.role_label
  const map = { staff: 'スタッフ', submgr: '副店長', mgr: '店長' }
  return map[s.role_code] || '―'
}

async function fetchList () {
  const kw = (keyword.value || '').trim()
  const params = kw
    ? { q: kw, search: kw, name: kw, _ts: Date.now() }
    : { ordering: '-id', limit: 50, _ts: Date.now() }

  // ★ 常に最新
  const staffs = await fetchStaffs(params, { cache: false })

  const today  = dayjs().format('YYYY-MM-DD')
  const shifts = await fetchStaffShifts({ date: today, _ts: Date.now() })
  const byId   = Object.fromEntries((Array.isArray(shifts)?shifts:[]).map(s => [s.staff_id, s]))

  results.value = (Array.isArray(staffs)?staffs:[]).map(s => {
    const sh = byId[s.id] || null
    return {
      ...s,
      _name: displayName(s),
      _role: displayRole(s),
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
  <div class="staff-list">
    <div class="d-flex gap-2 mb-2">
      <RouterLink :to="{ name: 'settings-staff-new' }" class="btn btn-primary d-flex align-items-center">
          新規登録
      </RouterLink>
      <div class="wrap position-relative ms-auto">
        <input
          v-model="keyword"
          class="form-control bg-white pe-3"
          placeholder="検索"
          @keyup.enter="fetchList"
          style="max-width: 200px;"
        >
        <button
          type="button"
          class="position-absolute top-50 end-0 translate-middle-y me-1"
          @click="fetchList"
          title="検索"
          aria-label="検索"
        >
            <IconSearch />
        </button>
      </div>
    </div>
    
    <div class="table-responsive">
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
  </div>
</template>


<style scoped lang="scss">

table{
  td,th{
    white-space: nowrap;
  }
}

</style>