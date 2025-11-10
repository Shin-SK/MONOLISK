<!-- src/views/AdminDriverForm.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { api } from '@/api'

/* ───────── ルーティング ───────── */
const route  = useRoute()
const router = useRouter()
const isEdit = !!route.params.id

/* ───────── フォーム ───────── */
const form = ref({
  user        : '',   // user PK
  store       : '',
  phone       : '',
  car_type    : '',
  number      : '',
  memo        : '',
  ng_casts    : [],
})
const hourly_rate = ref(null)

/* ───────── マスター ───────── */
const stores = ref([])
const casts  = ref([])

/* ───────── NG キャスト検索 ───────── */
const kw       = ref('')
const cand     = ref([])
const showCand = ref(false)

async function searchCast () {
  if (kw.value.length < 2) { showCand.value = false; return }
  cand.value  = await api.get('cast-profiles/', { params:{ search: kw.value } })
                         .then(r => r.data)
  showCand.value = cand.value.length > 0
}
function addNg (c) {
  if (!form.value.ng_casts.includes(c.id))
    form.value.ng_casts.push(c.id)
  kw.value = ''; showCand.value = false
}
function removeNg (id) {
  form.value.ng_casts =
    form.value.ng_casts.filter(x => x !== id)
}

/* ───────── データ取得 ───────── */
async function fetchMasters () {
  const [st, cs] = await Promise.all([
    api.get('stores/').then(r => r.data),
    api.get('cast-profiles/').then(r => r.data),
  ])
  ;[stores.value, casts.value] = [st, cs]
}

async function loadRate () {
  if (!isEdit) return
  const latest = await api.get('driver-rates/', {
    params:{ driver: route.params.id, ordering: '-effective_from', limit: 1 }
  }).then(r => r.data[0])
  hourly_rate.value = latest?.hourly_rate ?? null
}

async function fetchDriver () {
  if (!isEdit) return
  Object.assign(
    form.value,
    await api.get(`drivers/${route.params.id}/`).then(r => r.data),
  )
  await loadRate()
}

/* ───────── 保存 ───────── */
async function save () {
  try {
    /* ① Driver */
    let driverId
    if (isEdit) {
      await api.patch(`drivers/${route.params.id}/`, form.value)  // ← PUT → PATCH
      driverId = route.params.id
    } else {
      const { data } = await api.post('drivers/', form.value)
      driverId = data.id
    }

    /* ② 時給 upsert */
    if (hourly_rate.value !== null) {
      const today = dayjs().format('YYYY-MM-DD')
      const latest = await api.get('driver-rates/', {
        params:{ driver: driverId, effective_from: today, limit: 1 }
      }).then(r => r.data[0])

      if (latest) {
        await api.patch(`driver-rates/${latest.id}/`, {
          hourly_rate: hourly_rate.value
        })
      } else {
        await api.post('driver-rates/', {
          driver       : driverId,
          hourly_rate  : hourly_rate.value,
          effective_from: today
        })
      }
    }

    router.push('/drivers')
  } catch (e) {
    alert(e.response?.data?.detail || '保存失敗')
  }
}

/* ───────── 初期化 ───────── */
onMounted(async () => {
  await fetchMasters()
  await fetchDriver()
})
</script>

<template>
  <div
    class="container-fluid py-4"
    style="max-width:640px"
  >
    <!-- <h1 class="h4 mb-3">{{ isEdit ? 'ドライバー編集' : 'ドライバー登録' }}</h1> -->

    <!-- 基本情報 -->
    <div class="mb-3">
      <label class="form-label">ユーザー</label>
      <input
        v-model="form.user_name"
        class="form-control"
        :disabled="isEdit"
      >
    </div>

    <div class="mb-3">
      <label class="form-label">店舗</label>
      <select
        v-model="form.store"
        class="form-select"
      >
        <option
          v-for="s in stores"
          :key="s.id"
          :value="s.id"
        >
          {{ s.name }}
        </option>
      </select>
    </div>

    <div class="row mb-3">
      <div class="col-md-4">
        <label class="form-label">電話番号</label>
        <input
          v-model="form.phone"
          class="form-control"
        >
      </div>
      <div class="col-md-4">
        <label class="form-label">車種</label>
        <input
          v-model="form.car_type"
          class="form-control"
        >
      </div>
      <div class="col-md-4">
        <label class="form-label">ナンバー</label>
        <input
          v-model="form.number"
          class="form-control"
        >
      </div>
    </div>

    <!-- ★ 時給入力 -->
    <div class="mb-3 col-md-4">
      <label class="form-label">時給 (¥)</label>
      <input
        v-model.number="hourly_rate"
        type="number"
        class="form-control"
        min="0"
      >
    </div>

    <div class="mb-3">
      <label class="form-label">メモ</label>
      <textarea
        v-model="form.memo"
        rows="3"
        class="form-control"
      />
    </div>

    <!-- NG キャスト -->
    <div class="mb-3 position-relative">
      <label class="form-label">NG キャスト</label>
      <input
        v-model="kw"
        class="form-control mb-1"
        placeholder="キャスト名検索で追加"
        @input="searchCast"
      >

      <!-- 選択済み -->
      <div
        v-if="form.ng_casts.length"
        class="mt-2"
      >
        <span
          v-for="id in form.ng_casts"
          :key="id"
          class="badge bg-secondary me-2"
        >
          {{ casts.find(c => c.id === id)?.stage_name || id }}
          <button
            class="btn-close btn-close-white btn-sm ms-1"
            @click="removeNg(id)"
          />
        </span>
      </div>

      <!-- 検索候補 -->
      <ul
        v-if="showCand"
        class="list-group position-absolute w-100"
        style="z-index:5"
      >
        <li
          v-for="c in cand"
          :key="c.id"
          class="list-group-item list-group-item-action"
          @click="addNg(c)"
        >
          {{ c.stage_name }} / {{ c.store_name }}
        </li>
      </ul>
    </div>

    <button
      type="button"
      class="btn btn-primary"
      @click="save"
    >
      保存
    </button>
  </div>
</template>

