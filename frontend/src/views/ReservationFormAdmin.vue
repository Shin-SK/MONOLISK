<!-- src/views/ReservationFormAdmin.vue -->
<script setup>
/* =============================================================== *
 *  予約フォーム（管理者用）
 *  - 料金計算はすべてリアクティブに (VueUse asyncComputed で非同期も吸収)
 *  - “延長料金” や “手書き加算” をあとから UI に足すだけで合計へ反映
 * =============================================================== */

import { ref, computed, onMounted } from 'vue'
import { asyncComputed }            from '@vueuse/core'          // ★追加
import { useRoute, useRouter }      from 'vue-router'
import debounce                     from 'lodash.debounce'
import {
  /* ---------- API ---------- */
  getStores, getCustomers, getDrivers, getCourses,
  getOptions, getCastProfiles, getPrice,
  searchCustomers, createCustomer,
  createReservation, updateReservation, getReservation
} from '@/api'

/* ---------- 基本 ---------- */
const route  = useRoute()
const router = useRouter()
const isEdit = !!route.params.id   // id があれば編集

/* ---------- 予約（読み取り専用） ---------- */
const rsv = ref({ received_amount: 0 })

/* ---------- フォーム値 ---------- */
const form = ref({
  stores:          [],
  cast_profiles:   [],
  start_at:        '',
  course:          '',
  driver:          '',
  customer:        '',
  deposited_amount: 0,

  /* ← 将来拡張用の自由フィールドも先に置いておく */
  manual_extra:    0,   // 手書き加算
  extension_fee:   0,   // 延長料金
})

/* ---------- マスタ ---------- */
const opts = ref({
  stores:   [],
  customers:[],
  drivers:  [],
  courses:  [],
  options:  [],
  casts:    [],
})

/* ---------- マスタ取得 ---------- */
async function fetchMasters () {
  const [stores, customers, drivers, courses, options] = await Promise.all([
    getStores(), getCustomers(), getDrivers(), getCourses(), getOptions()
  ])
  opts.value = { stores, customers, drivers, courses, options, casts:[] }
  if (!isEdit && stores.length && form.value.stores.length === 0) {
    form.value.stores = [stores[0].id]    // 新規時: 先頭店舗を初期 ON
  }
}

/* ---------- 既存予約読み込み ---------- */
async function fetchReservation () {
  if (!isEdit) return
  const res = await getReservation(route.params.id)
  rsv.value = res
  Object.assign(form.value, {
    stores         : res.store ? [res.store] : [],
    cast_profiles  : res.casts.map(c => c.cast_profile.id),
    start_at       : res.start_at.slice(0,16),
    course         : res.casts[0]?.rank_course ?? '',
    driver         : res.driver,
    customer       : res.customer,
    deposited_amount : res.deposited_amount ?? 0,
    manual_extra     : 0,
    extension_fee    : 0,
  })
  selectedOptions.value = res.charges
    .filter(c => c.kind === 'OPTION')
    .map(c => c.option)
}

/* ---------- 店舗が変わったらキャスト再フェッチ ---------- */
import { watch } from 'vue'
watch(
  () => form.value.stores,
  async (stores=[]) => {
    form.value.cast_profiles = []
    if (!stores.length) { opts.value.casts = []; return }
    const lists = await Promise.all(stores.map(s => getCastProfiles(s)))
    /* id 重複を排除してマージ */
    opts.value.casts = Object.values(
      lists.flat().reduce((acc, c) => ({ ...acc, [c.id]: c }), {})
    )
  },
  { immediate:true }
)

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
function clearCustomer () { form.value.customer=''; phone.value=''; showList.value=false }

/* =============================================================== */
/*  💰 料金計算（完全リアクティブ）                                 */
/* =============================================================== */

/* 1. キャスト×コース基本料金（非同期計算） */
const castPriceSum = asyncComputed(
  async () => {
    if (!form.value.course || !form.value.cast_profiles.length) return 0
    const prices = await Promise.all(
      form.value.cast_profiles.map(id => getPrice(id, form.value.course))
    )
    return prices.reduce((a,b)=>a+b, 0)
  },
  0
)

/* 2. オプション料金 */
const optionPriceSum = computed(() =>
  selectedOptions.value
    .map(id => opts.value.options.find(o => o.id === id)?.default_price ?? 0)
    .reduce((a,b)=>a+b, 0)
)

/* 3. 手書き・延長など自由枠 */
const manualSum    = computed(() => Number(form.value.manual_extra ) || 0)
const extensionSum = computed(() => Number(form.value.extension_fee) || 0)

/* 4. 合計 */
const price = computed(
  () => castPriceSum.value + optionPriceSum.value + manualSum.value + extensionSum.value
)

/* ---------- 初期ロード ---------- */
onMounted(async () => {
  await fetchMasters()
  await fetchReservation()
})

/* ---------- 保存 ---------- */
async function save () {
  const minutes =
    opts.value.courses.find(c => c.id === form.value.course)?.minutes ?? 0

  const toId = v => (v && typeof v === 'object') ? v.id : v

  const payload = {
    store  : toId(form.value.stores[0] ?? null),
    driver : toId(form.value.driver) || null,
    customer  : form.value.customer || null,
    start_at  : new Date(form.value.start_at).toISOString(),
    total_time: minutes,
    deposited_amount : form.value.deposited_amount,
    casts: form.value.cast_profiles.map(cpId => ({
      cast_profile: toId(cpId),
      course      : toId(form.value.course),
    })),
    charges: [
      /* オプション */
      ...selectedOptions.value.map(id => ({ kind:'OPTION', option:id, amount:null })),
      /* 手書き & 延長は “自由課金” としてバックエンド実装するとき用の例 */
      ...(manualSum.value    ? [{ kind:'MANUAL',  label:'手書き', amount:manualSum.value }] : []),
      ...(extensionSum.value ? [{ kind:'EXTEND',  label:'延長',   amount:extensionSum.value }] : []),
    ],
  }

  try {
    isEdit
      ? await updateReservation(route.params.id, payload)
      : await createReservation(payload)
    router.push('/reservations')
  } catch (e) {
    console.error(e.response?.data)
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
    <!-- 店舗ボタン：チェックボックス -->
    <div class="d-flex flex-wrap gap-3" role="group" aria-label="Stores">
      <template v-for="s in opts.stores" :key="s.id">
        <input  class="btn-check" type="checkbox"
                :id="`store-${s.id}`"
                v-model="form.stores"
                :value="s.id" autocomplete="off">

        <label  class="btn btn-outline-primary"
                :class="{ active: form.stores.includes(s.id) }"
                :for="`store-${s.id}`">
          {{ s.name }}
        </label>
      </template>
    </div>



<!-- キャスト：チェックボックス -->
<div class="d-flex flex-wrap gap-4" role="group" aria-label="Casts">
  <template v-for="c in opts.casts" :key="c.id">
    <!-- hidden checkbox -->
    <input  class="btn-check"
            type="checkbox"
            :id="`cast-${c.id}`"
            v-model="form.cast_profiles"
            :value="c.id" autocomplete="off">

    <!-- 表示用ボタン -->
    <label  class="btn btn-outline-primary d-flex align-items-center gap-2"
            :class="{ active: form.cast_profiles.includes(c.id) }"
            :for="`cast-${c.id}`">

      <!-- ▼アバター画像（丸型 32×32）-->
      <img :src="c.photo_url || '/static/img/cast-default.png'"
           alt=""
           class="rounded-circle border"
           style="width:32px;height:32px;object-fit:cover;">

      <!-- 名前と☆ -->
      <span>{{ c.stage_name }}（☆{{ c.star_count }}）</span>
    </label>
  </template>
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
