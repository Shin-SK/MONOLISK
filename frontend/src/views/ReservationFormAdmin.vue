<!-- src/views/ReservationFormAdmin.vue -->
<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute, useRouter }             from 'vue-router'
import debounce                            from 'lodash.debounce'
import {
  getStores, getCustomers, getDrivers, getCourses,
  getOptions, getCastProfiles, getPrice,
  searchCustomers, createCustomer,
  createReservation, updateReservation, getReservation
} from '@/api'

/* ---------- 基本 ---------- */
const route  = useRoute()
const router = useRouter()
const isEdit = !!route.params.id          // id があれば編集

/* ---------- 予約（読み取り用） ---------- */
const rsv = ref({ received_amount: 0 })                    // ここに GET した予約全体を保持

/* ---------- form ---------- */
const form = ref({
  store:'', cast_profile:'', start_at:'',
  course:'', driver:'', customer:'',
  deposited_amount: 0                     // 入金額（管理者入力）
})

/* ---------- masters ---------- */
const price = ref(0)
const opts  = ref({
  stores:[], customers:[], drivers:[],
  courses:[], casts:[], options:[]
})

/* ---------- マスタ取得 ---------- */
async function fetchMasters () {
  const [stores, customers, drivers, courses, options] = await Promise.all([
    getStores(), getCustomers(), getDrivers(), getCourses(), getOptions()
  ])
  opts.value = { stores, customers, drivers, courses, options, casts:[] }
  if (!isEdit) form.value.store = stores[0]?.id ?? ''   // 新規時: 1 行目を初期選択
}

/* ---------- 既存予約読み込み ---------- */
async function fetchReservation () {
  if (!isEdit) return
  const res   = await getReservation(route.params.id)
  rsv.value   = res                                  // 一覧表示等の読み取り用
  Object.assign(form.value, {
    store            : res.store,
    cast_profile     : res.casts[0]?.cast_profile ?? '',
    start_at         : res.start_at.slice(0,16),
    course           : res.casts[0]?.rank_course  ?? '',
    driver           : res.driver,
    customer         : res.customer,
    deposited_amount : res.deposited_amount ?? 0
  })
  /* 既存 Option → チェック状態に */
  selectedOptions.value = res.charges
    .filter(c => c.kind === 'OPTION')
    .map(c => c.option)
}

/* ---------- オプション選択 ---------- */
const selectedOptions = ref([])

/* ---------- 顧客検索 ---------- */
const phone      = ref('')
const candidates = ref([])
const showList   = ref(false)

const fetchCandidates = debounce(async () => {
  if (phone.value.length < 3) { showList.value = false; return }
  candidates.value = await searchCustomers(phone.value)
  showList.value   = candidates.value.length > 0
}, 400)

const selectedCustomer = computed(
  () => opts.value.customers.find(c => c.id === form.value.customer) || null
)

function choose (c) {
  if (!opts.value.customers.some(x => x.id === c.id)) opts.value.customers.push(c)
  form.value.customer = c.id
  phone.value   = c.phone
  showList.value= false
}

async function registerNew () {
  const name = prompt('顧客名'); if (!name) return
  const address = prompt('住所') || ''
  const newCust = await createCustomer({ name, phone: phone.value, address })
  choose(newCust)
}

function clearCustomer () {
  form.value.customer = ''
  phone.value         = ''
  candidates.value    = []
  showList.value      = false
}

/* ---------- 動的見積 ---------- */
watch([() => form.value.cast_profile, () => form.value.course], async ([cp, cs]) => {
  price.value = (cp && cs) ? await getPrice(cp, cs) : 0
})

/* ---------- 初期ロード ---------- */
onMounted(async () => {
  await fetchMasters()
  opts.value.casts = await getCastProfiles()
  await fetchReservation()
})

/* ---------- 保存 ---------- */
async function save () {
  const minutes =
    opts.value.courses.find(c => c.id === form.value.course)?.minutes ?? 0

  const payload = {
    store      : form.value.store,
    driver     : form.value.driver   || null,
    customer   : form.value.customer || null,
    start_at   : new Date(form.value.start_at).toISOString(),
    total_time : minutes,
    deposited_amount : form.value.deposited_amount,
    casts      : [
      { cast_profile: form.value.cast_profile, rank_course: form.value.course }
    ],
    charges    : selectedOptions.value.map(id => ({
                   kind:'OPTION', option:id, amount:null
                 }))
  }

  try {
    isEdit
      ? await updateReservation(route.params.id, payload)
      : await createReservation(payload)
    router.push('/reservations')
  } catch (e) {
    console.log(e.response?.data)
    alert(e.response?.data?.detail || 'バリデーションエラー')
  }
}
</script>



<template>
<div class="container py-4">
  <h1 class="h3 mb-4">
    管理者用ページ {{ isEdit ? `予約 #${route.params.id} 編集` : '新規予約' }}
  </h1>

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
                 v-model="selectedOptions" :value="o.id">
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

    <!-- 顧客（電話検索） -->
    <div class="col-md-6 position-relative">
      <label class="form-label">顧客電話</label>

      <!-- 入力 -->
      <input v-if="!selectedCustomer" v-model="phone" @input="fetchCandidates"
             class="form-control" placeholder="090…" />

      <!-- 候補 -->
      <ul v-if="showList" class="list-group position-absolute w-100 z-3">
        <li v-for="c in candidates" :key="c.id"
            class="list-group-item list-group-item-action"
            @click="choose(c)">
          {{ c.name }} / {{ c.phone }}
        </li>
        <li class="list-group-item list-group-item-action text-primary"
            @click="registerNew">＋ 新規顧客を登録</li>
      </ul>

      <!-- 選択済み表示 -->
      <div v-if="selectedCustomer" class="mt-2 p-2 bg-light rounded">
        {{ selectedCustomer.name }}（{{ selectedCustomer.phone }}）
        <button class="btn btn-sm btn-outline-secondary ms-2" @click="clearCustomer">
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

    <!-- テンプレート：受取と入金の 2 つ表示 -->
    <div class="col-md-6">
      <label class="form-label">受取金額</label>
      <input type="number" class="form-control" v-model.number="rsv.received_amount" disabled />
    </div>
    <div class="col-md-6">
      <label class="form-label">入金額</label>
      <input type="number" class="form-control" v-model.number="form.deposited_amount" />
    </div>

    <div class="col-12 text-end">
      <button class="btn btn-primary" @click="save">保存</button>
    </div>
  </div>
</div>
</template>
