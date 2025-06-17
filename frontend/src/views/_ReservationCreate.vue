<!-- src/views/ReservationCreate.vue -->
<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useRouter }             from 'vue-router'
import debounce                  from 'lodash.debounce'
import {
  getStores, getDrivers, getCourses, getCastProfiles,
  getOptions,                      // ★ 追加
  getPrice, searchCustomers, createCustomer, createReservation
} from '@/api'

/* ---------- router ---------- */
const router = useRouter()

/* ---------- form ---------- */
const form = ref({
  store: '', cast_profile: '', start_at: '',
  course: '', driver: '', customer: ''
})

/* ---------- masters ---------- */
const price = ref(0)
const opts  = ref({
  stores:[], drivers:[], courses:[], casts:[],
  customers:[], options:[]           // ★ options を保持
})

const fetchMasters = async () => {
  const [stores, drivers, courses, options] = await Promise.all([
    getStores(), getDrivers(), getCourses(), getOptions()   // ★
  ])
  opts.value = { ...opts.value, stores, drivers, courses, options }
  form.value.store = stores[0]?.id ?? ''
}

onMounted(async () => {
  await fetchMasters()
  opts.value.casts = await getCastProfiles()
})

/* ---------- option 選択 ---------- */
const selectedOptions = ref([])            // ★ チェックボックス用

/* ---------- phone auto-complete ---------- */
const phone       = ref('')
const candidates  = ref([])
const showList    = ref(false)

const fetchCandidates = debounce(async () => {
  if (phone.value.length < 3) { showList.value = false; return }
  candidates.value = await searchCustomers(phone.value)
  showList.value   = candidates.value.length > 0
}, 400)

/* 選択済み顧客 (ラベル表示用) */
const selectedCustomer = computed(() =>
  opts.value.customers.find(c => c.id === form.value.customer) || null
)

/* 候補クリック */
const choose = c => {
  if (!opts.value.customers.some(x => x.id === c.id)) {
    opts.value.customers.push(c)
  }
  form.value.customer = c.id
  phone.value         = c.phone
  showList.value      = false
}

/* 新規顧客登録（簡易 prompt） */
const registerNew = async () => {
  const name    = prompt('顧客名')
  if (!name) return
  const address = prompt('住所') || ''
  const newCust = await createCustomer({ name, phone: phone.value, address })
  choose(newCust)
}

/* クリアして再検索 */
const clearCustomer = () => {
  form.value.customer = ''
  phone.value         = ''
  candidates.value    = []
  showList.value      = false
}

/* ---------- 動的見積 ---------- */
watch([() => form.value.cast_profile, () => form.value.course], async ([cp, crs]) => {
  price.value = (cp && crs) ? await getPrice(cp, crs) : 0
})

/* ---------- 保存 ---------- */
const save = async () => {
  const minutes = opts.value.courses.find(c => c.id === form.value.course)?.minutes ?? 0

  const payload = {
    store      : form.value.store,
    driver     : form.value.driver   || null,
    customer   : form.value.customer || null,
    start_at   : new Date(form.value.start_at).toISOString(),
    total_time : minutes,
    casts      : [
      { cast_profile: form.value.cast_profile, rank_course: form.value.course }
    ],
    charges    : selectedOptions.value.map(id => ({      // ★ ここ
                    kind:'OPTION', option:id, amount:null }))
  }

  try {
    await createReservation(payload)
    router.push('/reservations')
  } catch (e) {
    const msg = e.response?.data?.detail || 'バリデーションが起動しました。NGがあります。'
    alert(msg)
  }
}
</script>


<template>
<div class="container py-4">
  <h1 class="h3 mb-4">新規予約</h1>

  <div class="row gy-3">
    <!-- 店舗 -->
    <div class="col-12">
      <label class="form-label">店舗</label>
      <select v-model="form.store" class="form-select">
        <option v-for="s in opts.stores" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>

    <!-- キャスト -->
    <div class="col-12">
      <label class="form-label">キャスト</label>
      <div class="list-group">
        <label v-for="c in opts.casts" :key="c.id"
               class="list-group-item list-group-item-action d-flex align-items-center gap-2"
               :class="{active: form.cast_profile===c.id}">
          <input class="form-check-input mt-0" type="radio"
                 v-model.number="form.cast_profile" :value="c.id">
          <span>{{ c.stage_name }}（☆{{ c.star_count }}）</span>
        </label>
      </div>
    </div>

    <!-- 開始日時 -->
    <div class="col-md-6">
      <label class="form-label">開始日時</label>
      <input type="datetime-local" v-model="form.start_at" class="form-control">
    </div>

    <!-- コース -->
    <div class="col-md-6">
      <label class="form-label">コース</label>
      <select v-model="form.course" class="form-select">
        <option v-for="c in opts.courses" :key="c.id" :value="c.id">
          {{ c.minutes }}min {{ c.is_pack ? '（パック）' : '' }}
        </option>
      </select>
    </div>

    <!-- オプション -->
    <div class="col-12">
      <label class="form-label">オプション</label>
      <div class="list-group">
        <label v-for="o in opts.options" :key="o.id"
              class="list-group-item d-flex align-items-center gap-2">
          <input class="form-check-input mt-0" type="checkbox"
                :value="o.id" v-model="selectedOptions">
          <span>{{ o.name }}（¥{{ o.default_price.toLocaleString() }}）</span>
        </label>
      </div>
    </div>

    <!-- ドライバー -->
    <div class="col-md-6">
      <label class="form-label">ドライバー</label>
      <select v-model="form.driver" class="form-select">
        <option value="">― 未指定 ―</option>
        <option v-for="d in opts.drivers" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
    </div>


  <!-- 顧客（電話検索＋候補表示） -->
  <div class="col-md-6 position-relative">
    <label class="form-label">顧客電話</label>

    <!-- 電話入力は、未選択のときだけ表示 -->
    <input v-if="!selectedCustomer"
          v-model="phone"
          @input="fetchCandidates"
          class="form-control" placeholder="090…" />

    <!-- 候補リスト -->
    <ul v-if="showList" class="list-group position-absolute w-100 z-3">
      <li v-for="c in candidates" :key="c.id"
          class="list-group-item list-group-item-action"
          @click="choose(c)">
        {{ c.name }} / {{ c.phone }}
      </li>
      <li class="list-group-item list-group-item-action text-primary"
          @click="registerNew">
        ＋ 新規顧客を登録
      </li>
    </ul>

    <!-- 選択済み表示 -->
    <div v-if="selectedCustomer" class="mt-2 p-2 bg-light rounded">
      選択顧客：{{ selectedCustomer.name }}（{{ selectedCustomer.phone }}）
      <button class="btn btn-sm btn-outline-secondary ms-2"
              @click="clearCustomer">
        変更
      </button>
    </div>
  </div>


    <!-- 見積 -->
    <div class="col-12">
      <div class="alert alert-info">
        現在の見積 <strong>{{ price.toLocaleString() }}</strong> 円
      </div>
    </div>

    <div class="col-12 text-end">
      <button class="btn btn-primary" @click="save">保存</button>
    </div>
  </div>
</div>
</template>
