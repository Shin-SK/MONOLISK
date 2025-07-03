<script setup>
import { ref, onMounted } from 'vue'
import { useRouter }      from 'vue-router'
import dayjs              from 'dayjs'
import { getAllDriverShifts, getDrivers, getStores } from '@/api'
import { useUser } from '@/stores/useUser'

const router    = useRouter()
const userStore  = useUser() 
const date      = ref(dayjs().format('YYYY-MM-DD'))
const storeId   = ref('')
const filterId  = ref('')

const stores    = ref([])
const drivers   = ref([])
const rows      = ref([])

/* ---------- マスタ ---------- */
async function fetchMasters () {
  stores.value  = await getStores()
  drivers.value = await getDrivers()
}

/* ---------- 一覧 ---------- */
async function fetchList () {
  // ① 勤怠レコードをまとめて取得（date フィルタだけ掛ける）
  const recs = await getAllDriverShifts({ date: date.value })

  const byDriver = Object.fromEntries(
    recs.map(r => [r.driver, r])   // driver_id → 勤怠レコード
  )

  // ② ドライバーマスタ基準で必ず全員表示
  rows.value = drivers.value
    .filter(d => !storeId.value  || d.store === +storeId.value)
    .filter(d => !filterId.value || d.id    === +filterId.value)
    .map(d => {
      const r = byDriver[d.id] || {}
      return {
        driverId      : d.id,
        driverName    : d.name,
        storeName     : stores.value.find(s => s.id === d.store)?.name || '',
        recordPk      : r.id || null,
        clockInAt     : r.clock_in_at,
        clockOutAt    : r.clock_out_at,
        totalReceived : r.total_received,
        diff          : r.diff
      }
    })
}


/* ---------- 遷移 ---------- */
function goDetail (row) {
   if (!row.recordPk && !userStore.isStaff)
     return alert('このドライバーはまだ出勤していません')
 
   const routeName = row.recordPk
     ? 'driver-shift-detail'        // shiftId あり
     : 'driver-shift-by-driver'     // 代理出勤用
   router.push({
     name  : routeName,
     params: row.recordPk
       ? { shiftId: row.recordPk }
       : { driverId: row.driverId }
   })
}


onMounted(async () => {
  await fetchMasters()
  await fetchList()
})
</script>

<template>
  <div class="container-fluid py-4">
    <h3 class="mb-4">ドライバー勤怠一覧</h3>

    <!-- フィルタ -->
    <div class="row g-2 align-items-end mb-3">
      <div class="col-auto">
        <input type="date" v-model="date" class="form-control" @change="fetchList">
      </div>
      <div class="col-auto">
        <select v-model="storeId" class="form-select" @change="fetchList">
          <option value="">全店舗</option>
          <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="col-auto">
        <select v-model="filterId" class="form-select" @change="fetchList">
          <option value="">全ドライバー</option>
          <option v-for="d in drivers" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>
    </div>

    <!-- 一覧 -->
    <table class="table table-sm">
      <thead class="table-light">
        <tr>
          <th>Driver ID</th><th>ドライバー</th><th>店舗</th>
          <th>出勤</th><th>退勤</th>
          <th class="text-end">総受取金</th>
          <th class="text-end">差分</th>
          <th></th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="r in rows" :key="r.driverId">
          <td>{{ r.driverId }}</td>
          <td>{{ r.driverName }}</td>
          <td>{{ r.storeName }}</td>

          <td>{{ r.clockInAt  ? new Date(r.clockInAt ).toLocaleTimeString() : '—' }}</td>
          <td>{{ r.clockOutAt ? new Date(r.clockOutAt).toLocaleTimeString() : '—' }}</td>

          <td class="text-end">{{ (r.totalReceived || 0).toLocaleString() }}</td>
          <td class="text-end" :class="{ 'text-danger': (r.diff || 0) !== 0 }">
            {{ (r.diff || 0).toLocaleString() }}
          </td>

          <td>
            <button class="btn btn-sm btn-outline-primary" @click="goDetail(r)">
              詳細
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
