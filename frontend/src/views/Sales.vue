<!-- ClosingList.vue ※全文貼り替え -->

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import dayjs from 'dayjs'
import { api } from '@/api'
import { useRouter } from 'vue-router'

/* ──────────────── state ──────────────── */
const stores      = ref([])
const rows        = ref([])
const summary     = reactive({ period: 0, today: 0, month: 0 })
const showFilter  = ref(false)

const router = useRouter()

/* 「指定期間」金額を表示するか（本日は非表示） */
const showPeriod = computed(() =>
  q.period !== 'today' || q.period === 'range'
)

/* ──────────────── 検索フォーム ──────────────── */
const q = reactive({
  period : 'today',      // today | yesterday | week | all | range
  from   : '',
  to     : '',
  store  : ''
})

/* ──────────────── 初期ロード ──────────────── */
onMounted(async () => {
  stores.value  = await api.get('stores/').then(r => r.data)
  await search()                            // デフォルト＝本日
})

/* ──────────────── プリセット変更監視 ──────────────── */
watch(() => q.period, newVal => {
  if (['today', 'yesterday', 'week', 'all'].includes(newVal)) {
    search()                                // range は手動検索
  }
})

/* ──────────────── 検索メイン ──────────────── */
async function search () {
  /* ① 予約一覧 */
  const listParams = buildListParams()
  rows.value = await api.get('reservations/', {
    params: { ...listParams,
      with_entries : 1,
      with_options : 1,
      with_charges : 1
    }
  }).then(r => r.data)

  /* ② 指定期間サマリー（total）*/
  const sumParams  = buildSumParams()
  if (showPeriod.value) {
    const periodSum = await api.get('sales/summary/', { params: sumParams })
                               .then(r => r.data)
    summary.period = periodSum.total ?? 0
  } else {
    summary.period = 0                            // 表示しないときは 0
  }

  /* ③ 今日・今月サマリー（store のみ固定）*/
  const storeSum = await api.get('sales/summary/', { params: q.store ? { store: q.store } : {}})
  summary.today = storeSum.today_total  ?? 0 
  summary.month = storeSum.month_total ?? 0
}

/* ──────────────── 一覧用パラメータ ────────────────
   （日付キー: from_date / to_date）*/
function buildListParams () {
  const today  = dayjs().format('YYYY-MM-DD')
  const monday = dayjs().startOf('week').add(1, 'day')   // ISO 週始め
  const p = {}
    if (q.store) p.store = q.store

  switch (q.period) {
    case 'today':
      p.from_date = p.to_date = today; break
    case 'yesterday': {
      const y = dayjs().subtract(1, 'day').format('YYYY-MM-DD')
      p.from_date = p.to_date = y; break
    }
    case 'week':
      p.from_date = monday.format('YYYY-MM-DD')
      p.to_date   = today; break
    case 'range':
      if (q.from) p.from_date = q.from
      if (q.to)   p.to_date   = q.to
      break
    /* all → 期間指定なし */
  }
  return p
}

/* ──────────────── サマリー用パラメータ ────────────────
   （日付キー: from / to）*/
function buildSumParams () {
  const today  = dayjs().format('YYYY-MM-DD')
  const monday = dayjs().startOf('week').add(1, 'day')
  const base   = { store: q.store }

  switch (q.period) {
    case 'today':
      return { ...base, from: today, to: today }
    case 'yesterday': {
      const y = dayjs().subtract(1, 'day').format('YYYY-MM-DD')
      return { ...base, from: y, to: y }
    }
    case 'week':
      return {
        ...base,
        from: monday.format('YYYY-MM-DD'),
        to  : today
      }
    case 'range':
      return {
        ...base,
        ...(q.from && { from: q.from }),
        ...(q.to   && { to  : q.to   })
      }
    /* all → 日付指定なし */
    default:
      return base
  }
}
</script>




<template>
  <div class="sales container-fluid py-4">
    <!-- ── サマリー ── -->
    <div class="d-flex gap-2 summary">
      <div class="item">
        <span class="head">本日の総売上</span>
        <span class="cont">¥{{ (summary.today ?? 0).toLocaleString() }}</span>
      </div>
      <div class="item">
        <span class="head">今月の総売上</span>
        <span class="cont">¥{{ (summary.month ?? 0).toLocaleString() }}</span>
      </div>
      <div class="item">
        <span class="head">指定期間合計</span>
        <span class="cont">¥{{ summary.period?.toLocaleString?.() || '–' }}</span>
      </div>
    </div>

    <!-- ── プリセット期間 & 絞り込みボタン ── -->
    <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
      <!-- 左: プリセット期間 -->
      <div class="btn-group flex-wrap">
        <input
          id="btn-today"
          v-model="q.period"
          class="btn-check"
          type="radio"
          value="today"
        >
        <label
          class="btn btn-outline-primary"
          for="btn-today"
        >本日</label>

        <input
          id="btn-yest"
          v-model="q.period"
          class="btn-check"
          type="radio"
          value="yesterday"
        >
        <label
          class="btn btn-outline-primary"
          for="btn-yest"
        >昨日</label>

        <input
          id="btn-week"
          v-model="q.period"
          class="btn-check"
          type="radio"
          value="week"
        >
        <label
          class="btn btn-outline-primary"
          for="btn-week"
        >今週</label>

        <input
          id="btn-all"
          v-model="q.period"
          class="btn-check"
          type="radio"
          value="all"
        >
        <label
          class="btn btn-outline-primary"
          for="btn-all"
        >全期間</label>
      </div>

      <!-- 右: 絞り込みトグル -->
      <button
        class="btn btn-secondary"
        @click="showFilter = !showFilter"
      >
        {{ showFilter ? '閉じる' : '絞り込み' }}
      </button>
    </div>


    <!-- ── 詳細絞り込みパネル ── -->
    <form
      v-if="showFilter"
      class="card p-3 mb-3"
      @submit.prevent="search"
    >
      <div class="row g-3 align-items-end">
        <div class="col-md-4">
          <label class="form-label">期間指定</label>
          <div class="d-flex gap-1">
            <input
              v-model="q.from"
              type="date"
              class="form-control"
            >
            <span class="align-self-center">–</span>
            <input
              v-model="q.to"
              type="date"
              class="form-control"
            >
          </div>
        </div>

        <div class="col-md-3">
          <label class="form-label">店舗</label>
          <select
            v-model="q.store"
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

        <div class="col-md-2 text-end">
          <button class="btn btn-success px-4">
            検索
          </button>
        </div>
      </div>
    </form>


    <!-- ③ 一覧 -->
    <table class="table table-sm">
      <thead>
        <tr>
          <th>日付</th><th>開始</th><th>キャスト</th><th>顧客</th>
          <th class="text-end">
            見積
          </th><th class="text-end">
            受取
          </th>
          <th class="text-end">
            差額
          </th><th>リンク</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in rows"
          :key="r.id"
          :class="{ 'table-danger': r.discrepancy_flag }"
        >
          <td>{{ dayjs(r.start_at).format('YYYY-MM-DD') }}</td>
          <td>{{ dayjs(r.start_at).format('HH:mm') }}</td>
          <td>{{ r.cast_names?.join(', ') }}</td>
          <td>{{ r.customer_name }}</td>

          <td class="text-end">
            {{ (r.expected_total ?? r.expected_amount ?? 0).toLocaleString() }}
          </td>
          <td class="text-end">
            {{ (r.received_amount ?? 0).toLocaleString() }}
          </td>
          <td class="text-end">
            {{ ((r.received_amount ?? 0) - (r.expected_total ?? r.expected_amount ?? 0)).toLocaleString() }}
          </td>
          <td>
            <button
              class="btn btn-link p-0"
              @click="router.push(`/reservations/${r.id}`)"
            >
              詳細
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
