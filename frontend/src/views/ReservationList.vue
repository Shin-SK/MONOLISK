<!-- src/views/ReservationList.vue -->
<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import {
  getStores,getCastProfiles,getReservations,deleteReservations, getReservationChoices,
} from '@/api'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'

/* ────────── 状態 ────────── */
const router    = useRouter()
const stores    = ref([])
const casts     = ref([])
const rows      = ref([])
const selected  = ref(new Set())
const choices = ref({ status: [] })

// util: API → 常に配列へ整形
const normalizeCasts = (raw) =>
  (Array.isArray(raw) ? raw : raw?.results ?? []).filter(c => c && c.id);


// ---------------- ページネーション ----------------
const perPage     = 30
const page        = ref(1)
const totalCount  = ref(0)
const maxPage     = computed(() => Math.ceil(totalCount.value / perPage) || 1)
const canPrev     = computed(() => page.value > 1)
const canNext     = computed(() => page.value < maxPage.value)

/* ────────── 親から初期フィルタ ────────── */
const props = defineProps({
  initFilters: { type: Object, default: () => ({}) }
})
const form = ref({
  store:'', cast:'', date:'',
  ...props.initFilters
})

/* ────────── 日付関係 ────────── */
const today = new Date() 
const yyyy_mm_dd = d => d.toISOString().slice(0,10)
function setRelative (days) {
  const d = new Date()
  d.setDate(d.getDate() + days)
  form.value.date = yyyy_mm_dd(d)
}
function clearDate () { form.value.date = '' }

const dateInput = ref(null)
function openPicker () {
  dateInput.value?.showPicker?.() || dateInput.value?.click()
}
/* ① フォーマッタを用意 ------------- */
const fmtDate = iso => dayjs(iso).format('YYYY/MM/DD')
const fmtTime = iso => dayjs(iso).format('HH:mm')



/* ────────── 終了時刻つくる ────────── */
const calcEnd   = row => {
  // ─ 合計分数を決定 ─
  const minutes =
    row.total_time                                   // ① total_time が来ていれば最優先
    ?? (row.courses?.[0]?.minutes ?? 0)              // ② 先頭キャストのコース分
       + ((row.extend_blocks ?? 0) * 30)             //    ＋延長 30 分ブロック
  return dayjs(row.start_at).add(minutes, 'minute')  // dayjs インスタンス
}

const endDate = row => calcEnd(row).format('YYYY/MM/DD')
const endTime = row => calcEnd(row).format('HH:mm')

/* ピックアップ／ドロップオフ用に共通ヘルパ */
const getDriver = (row, role) =>
  (row.drivers ?? []).find(d => d.role === role) || null


/* ────────── 店舗が変わったらキャストを再取得 ────────── */
watch(() => form.value.store, async id => {
  form.value.cast = ''
  // casts.value = await getCastProfiles(id || undefined)
  casts.value = normalizeCasts(await getCastProfiles({ store: id }))
})

/* ────────── 検索本体 ────────── */
async function search () {
  const raw = await getReservations({
    ...form.value,
    ordering     : '-start_at',
    limit        : perPage,
    offset       : perPage * (page.value - 1),
    with_entries : 1,
    with_options : 1,
    with_charges : 1        // ←★ここが無いと課金金額が来ない
  })

  const list = raw.results ?? raw            // ← pages でも旧配列でも対応
  totalCount.value = raw.count ?? list.length

  rows.value = list
    .filter(Boolean)
    .map(r => {

    /* 手入力売上／経費 */
    const revenue = (r.manual_entries ?? [])
      .filter(e => e.entry_type === 'revenue')
      .reduce((t, e) => t + (+e.amount || 0), 0)

    const expense = (r.manual_entries ?? [])
      .filter(e => e.entry_type === 'expense')
      .reduce((t, e) => t + (+e.amount || 0), 0)

    /* オプション課金合計 */
    let optionSum = (r.charges ?? [])
      .filter(c => c.kind === 'OPTION')
      .reduce((t, c) => t + Number(c.amount ?? c.price ?? 0), 0)

    const card_amount = (r.payments ?? [])
      .filter(p => p.method === 'card')
      .reduce((t, p) => t + Number(p.amount || 0), 0)

    const net_cash   = (r.received_amount ?? 0) - (r.change_amount ?? 0)
    const expected = r.expected_total ?? r.expected_amount ?? 0
    const totalPaid  = card_amount + net_cash 
    const diff      = totalPaid - expected     
    const isDiffAlert = diff !== 0 && r.status === 'CASH_COLLECT'

    if (optionSum === 0 && Array.isArray(r.options)) {
      optionSum = r.options
        .reduce((t, o) => t + Number(o.amount ?? o.price ?? o.default_price ?? 0), 0)
    }
    return {
      ...r,
      expected_total: r.expected_total,
      card_amount, diff, isDiffAlert,
    }
  })

}

/* ---------------------------------------------- *
 * ステータス → ラベル／色
 * ---------------------------------------------- */
const statusLabel = s =>
  choices.value.status.find(c => c[0] === s)?.[1] || s

const statusColor = s => ({
  CALL_PENDING : 'bg-secondary',
  CALL_DONE    : 'bg-info',
  BOOKED       : 'bg-warning',
  IN_SERVICE   : 'bg-danger',
  CASH_COLLECT : 'bg-primary',
}[s] || 'bg-light')

const statusRowClass = s => ({
  CALL_PENDING : 'table-secondary',  // 灰
  CALL_DONE    : 'table-info',       // 水
  BOOKED       : 'table-warning',    // 黄
  IN_SERVICE   : 'table-danger',    // 赤
  CASH_COLLECT : 'table-primary',    // 青
}[s] || '')


const diffRowClass  = flag => (flag ? 'table-danger' : '')
const diffCellClass = flag => (flag ? 'text-danger fw-bold' : '')

/* ────────── 表操作 ────────── */
async function resetForm () {
  form.value  = { store:'', cast:'', date:'' };
  casts.value = normalizeCasts(await getCastProfiles());
  page.value  = 1;
  await search();
}
function toggle (id) {
  selected.value.has(id)
    ? selected.value.delete(id)
    : selected.value.add(id)
}

const allChecked = computed({
  get: () => rows.value.length && selected.value.size === rows.value.length,
  set: v => { selected.value = v ? new Set(rows.value.map(r=>r.id)) : new Set() }
})

async function bulkDelete () {
  if (!confirm(`${selected.value.size} 件を削除します。よろしいですか？`)) return
  try {
    await deleteReservations([...selected.value])
    rows.value = rows.value.filter(r => !selected.value.has(r.id))
    selected.value.clear()
  } catch (e) {
    alert('削除に失敗しました')
    console.error(e)
  }
}

/* ────────── 初期化 ────────── */
onMounted(async () => {
  stores.value  = await getStores();
  casts.value   = normalizeCasts(await getCastProfiles());
  choices.value = await getReservationChoices();
  await search();
});
</script>





<template>
<div class="ReservationList container-fluid py-4">
	<!-- <h1 class="h3">予約一覧</h1> -->

<!-- ReservationList.vue ― 検索フォーム -->
  <div class="search">
    <form class="form search-row" @submit.prevent="search">
      <!-- 店舗ラジオ -->
      <fieldset class="field-group radio-items radio-store">
        <label class="radio-item">
          <input type="radio" value="" v-model="form.store" />
          <span>全店舗</span>
        </label>
        <label v-for="s in stores" :key="s.id" class="radio-item">
          <input type="radio" :value="s.id" v-model="form.store" />
          <span>{{ s.name }}</span>
        </label>
      </fieldset>

      <div class="search-wrap">
        <!-- キャストラジオ -->
        <fieldset class="field-group radio-cast radio-items" :disabled="!casts.length">
          <label v-for="c in casts" :key="c.id" class="radio-item">
            <input type="radio" :value="c.id" v-model="form.cast" />
            <img :src="c.photo_url" class="cast-icon" />
            <span>{{ c.stage_name }}</span>
          </label>
        </fieldset>

        <!-- 日付 -->
        <div class="field-group date-box">
          <!-- ① ショートカット -->
          <div class="button-area">
            <!-- 昨日／今日／明日ボタン -->
            <button
              type="button"
              :class="['btn btn-dark', { active: form.date === yyyy_mm_dd(new Date(today.setDate(today.getDate()-1))) }]"
              @click="setRelative(-1)"
            >昨日</button>

            <button
              type="button"
              :class="['btn btn-dark', { active: form.date === yyyy_mm_dd(new Date()) }]"
              @click="setRelative(0)"
            >今日</button>

            <button
              type="button"
              :class="['btn btn-dark', { active: form.date === yyyy_mm_dd(new Date(today.setDate(today.getDate()+1))) }]"
              @click="setRelative(1)"
            >明日</button>

            <!-- 日付指定ボタン（選択済み＝active） -->
            <button
              type="button"
              :class="['btn btn-dark', { active: form.date && !['昨日','今日','明日'].includes(form.date) }]"
              @click="openPicker"
            >日付指定</button>
              <!-- 隠れ input -->
              <input
                type="date"
                ref="dateInput"
                v-model="form.date"
                @change="$event.target.blur()"
                class="hidden-input"
              />
          </div>
          <div class="result">
              <span v-if="form.date" class="selected-date">{{ form.date }}</span>
              <button
                v-if="form.date"
                type="button"
                @click="clearDate"
              ><span class="material-symbols-outlined">close</span></button>
          </div>
        </div>
      </div>


      <!-- ボタン -->
      <div class="btn-wrap">
        <button type="submit" class="btn btn-dark btn-search">検索</button>
        <button type="button" class="btn btn-dark btn-reset" @click="resetForm">リセット</button>
        <button class="btn btn-dark btn-new" @click="router.push('/reservations/new')">
          新規予約
        </button>
      </div>

    </form>
  </div>


  <div class="list">
    <table class="table table-bordered table-hover align-middle table-striped">
      <thead class="table-dark">
        <tr>
          <th><input type="checkbox" v-model="allChecked" /></th>
          <th>ID</th>
          <th>キャスト</th>
          <th>開始</th>
          <th>顧客</th>
          <th>終了</th>
          <th>オプション</th>
          <th>迎え</th>
          <th>送り</th>
          <th>小計</th>
          <th>カード</th>
          <th>受取金</th>
          <th>お釣り</th>
          <!-- <th>入金</th> -->
        </tr>
      </thead>

      <tbody>
        <tr v-for="r in rows.filter(Boolean)"
          :key="r.id"
          @click="router.push(`/reservations/${r.id}`)"
          style="cursor: pointer;"
          :class="diffRowClass(r.isDiffAlert)">
          <td>
            <input
              type="checkbox"
              :checked="selected.has(r.id)"
              @change="toggle(r.id)"
            />
          </td>
          <td>
            <div><span class="badge bg-secondary">{{ r.id }}</span><span class="badge bg-secondary mx-2">{{ r.store_name }}</span></div>
            <span :class="['badge',statusColor(r.status)]">{{ statusLabel(r.status) }}</span>
          </td>
          <td>
            <img v-for="(p,i) in r.cast_photos"
            :key="i"
            :src="p"
            class="cast-icon me-1">
            {{ r.cast_names.join(', ') }}
          </td>
          <td>
            <span class="text-muted">
              {{ fmtDate(r.start_at) }}      <!-- 1 行目 : 日付 -->
            </span>
            <span class="d-block fw-bold fs-4">
              {{ fmtTime(r.start_at) }}      <!-- 2 行目 : 時刻 -->
            </span>
          </td>
          <td>
            <div><span class="badge bg-secondary">{{ r.courses.map(c => c.minutes + '分').join(', ') }}</span></div>
            {{ r.customer_name }}
          </td>
          <!-- ★ 新しい『終了』セル -->
          <td class="end-cell">
            <span class="text-muted">{{ endDate(r) }}</span>
            <span class="fw-bold fs-4 d-block">{{ endTime(r) }}</span>
          </td>
          <td>
            <template v-if="r.options && r.options.length">
              <span
                v-for="(o, i) in r.options"
                :key="i"
                class="badge bg-success me-2"
              >
                {{ o.name || '(自由課金)' }}
              </span>
            </template>
            <template v-else>―</template>
          </td>
          <td>
            <!-- ① ドライバーがいればバッジで表示 -->
            <span
              v-if="getDriver(r, 'PU')"
              class="badge bg-primary badge-lg"
            >
              {{ getDriver(r, 'PU').driver_name }}
            </span>

            <!-- ② いなければ従来のダッシュ -->
            <template v-else>―</template>
          </td>
          <td>
            <!-- ① ドライバーがいればバッジで表示 -->
            <span
              v-if="getDriver(r, 'PU')"
              class="badge bg-primary badge-lg"
            >
              {{ getDriver(r, 'DO').driver_name }}
            </span>

            <!-- ② いなければ従来のダッシュ -->
            <template v-else>―</template>
          </td>
          <td class="fw-bold">¥{{ (r.expected_total??r.expected_amount??0).toLocaleString() }}</td>
          <td class="fw-bold">¥{{ (r.card_amount ?? 0).toLocaleString() }}</td>
          <td class="fw-bold">¥{{ (r.received_amount??0).toLocaleString() }}</td>
          <td class="fw-bold position-relative">
            ¥{{ (r.change_amount ?? 0).toLocaleString() }}

            <!-- 普段は透明 / hover でフェードイン -->
            <span
              v-if="r.isDiffAlert"
              class="diff-badge badge bg-danger position-absolute top-0 end-0 translate-middle-y"
            >
              差額{{ r.diff > 0 ? '+' : '' }}¥{{ Math.abs(r.diff).toLocaleString() }}
            </span>
          </td>
          <!-- <td class="fw-bold">¥{{ (r.deposited_amount??0).toLocaleString() }}</td> -->
          <!-- <td>
            <button class="btn btn-link p-0"
                    @click="router.push(`/reservations/${r.id}`)">
              詳細
            </button>
          </td> -->
        </tr>
      </tbody>
    </table>
  </div>

    <div class="list-footer d-flex align-items-center justify-content-between">
      <button class="btn btn-danger mb-3" :disabled="!selected.size" @click="bulkDelete" >
        選択を削除
      </button>
      <div class="pagenation">
        <nav class="my-3 d-flex justify-content-center align-items-center gap-3">
          <button
            class="btn btn-outline-secondary"
            :disabled="!canPrev"
            @click="page-- ; search()"
          >
            ‹ Prev
          </button>

          <span>{{ page }} / {{ maxPage }}</span>

          <button
            class="btn btn-outline-secondary"
            :disabled="!canNext"
            @click="page++ ; search()"
          >
            Next ›
          </button>
        </nav>
      </div>
    </div>


</div>
</template>



<style scoped>
/* 通常は非表示 → 行 or セルに hover すると 0.9 までフェードイン */
.diff-badge {
  opacity: 0;
  transition: opacity .15s ease;
  pointer-events: none;   /* マウスイベントを透過 */
}
tr:hover .diff-badge,
td:hover .diff-badge {
  opacity: .9;
}
</style>