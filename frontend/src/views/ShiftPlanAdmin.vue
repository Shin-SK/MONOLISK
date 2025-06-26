<script setup>
import { ref, onMounted } from 'vue'
import { api, getShiftPlans, checkIn, checkOut } from '@/api'

const date   = ref(new Date().toISOString().slice(0,10))
const store  = ref('')
const stores = ref([])
const list   = ref([])   // 表示行
const casts  = ref([])   // 店舗キャスト候補

/* ---------- マスタ ---------- */
async function fetchStores () {
  stores.value = await api.get('stores/?simple=1').then(r => r.data)
  store.value  = stores.value[0]?.id ?? ''
}

/* ---------- 検索 ---------- */
async function fetchAll () {
  list.value  = await getShiftPlans({ date: date.value, store: store.value || undefined })
  // date を行に保持（新規行との一貫性のため）
  list.value  = list.value.map(r => ({ ...r, date: r.date || date.value }))
  casts.value = await api.get('cast-profiles/', { params:{ store: store.value } })
                     .then(r => r.data)
}

/* ---------- 新規行 ---------- */
function addRow () {
  list.value.push({
    id:null, date: date.value,
    cast_profile:'', start_at:'18:00', end_at:'23:00',
    is_checked_in:false
  })
}

/* ---------- 保存 ---------- */
async function save (row) {
  const payload = { ...row, store: store.value }
  if (row.id) {
    await api.patch(`shift-plans/${row.id}/`, payload)
  } else {
    const { data } = await api.post('shift-plans/', payload)
    Object.assign(row, data)          // id・is_checked_in など反映
  }
}

/* ---------- 削除 ---------- */
async function del (row, idx) {
  if (row.id) await api.delete(`shift-plans/${row.id}/`)
  list.value.splice(idx,1)
}

/* ---------- 打刻 ---------- */
async function toggleCheck (row) {
  if (!row.id) return   // 未保存行は無視

  const def  = new Date().toTimeString().slice(0,5)         // HH:MM
  const time = prompt('打刻時刻 (HH:MM) 空欄=現在', def) || def
  const at   = `${row.date}T${time}:00`

  row.is_checked_in
    ? await checkOut(row.id, at)
    : await checkIn (row.id, at)

  row.is_checked_in = !row.is_checked_in
}

onMounted(async () => { await fetchStores(); await fetchAll() })
</script>

<template>
<div class="container py-4">
  <h1 class="h4 mb-3">シフト管理</h1>

  <div class="d-flex gap-3 mb-3">
    <input type="date" v-model="date"  @change="fetchAll" class="form-control" style="max-width:180px">
    <select v-model="store" @change="fetchAll" class="form-select"  style="max-width:200px">
      <option value="">全店舗</option>
      <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
    </select>
    <button class="btn btn-primary" @click="addRow">＋ 追加</button>
  </div>

  <table class="table table-sm align-middle">
    <thead class="table-dark">
      <tr><th>日付</th><th>キャスト</th><th>開始</th><th>終了</th><th>状態</th><th>操作</th></tr>
    </thead>
    <tbody>
      <tr v-for="(r,i) in list" :key="i">
        <td><input type="date" v-model="r.date" class="form-control"></td>

        <td>
          <select v-model="r.cast_profile" class="form-select">
            <option value="" disabled>選択</option>
            <option v-for="c in casts" :key="c.id" :value="c.id">{{ c.stage_name }}</option>
          </select>
        </td>

        <td><input type="time" v-model="r.start_at" class="form-control"></td>
        <td><input type="time" v-model="r.end_at"   class="form-control"></td>

        <td>
          <span v-if="r.is_checked_in" class="badge bg-success">IN</span>
          <span v-else                 class="badge bg-secondary">未</span>
        </td>

        <td class="d-flex gap-2">
          <button class="btn btn-sm btn-primary"         @click="save(r)">保存</button>
          <button class="btn btn-sm btn-outline-danger"  @click="del(r,i)">削除</button>
          <button class="btn btn-sm"
                  :class="r.is_checked_in ? 'btn-warning' : 'btn-success'"
                  @click="toggleCheck(r)">
            {{ r.is_checked_in ? '退勤' : '出勤' }}
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</div>
</template>
