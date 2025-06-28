<!-- ClosingList.vue ※全文貼り替え -->

<script setup>
import { ref, reactive, onMounted } from 'vue'
import dayjs from 'dayjs'
import { api } from '@/api'

/* ── state ── */
const stores  = ref([])
const rows    = ref([])
const summary = reactive({ today: 0, month: 0 })

/* ── 検索フォーム ── */
const q = reactive({
  period: 'today',      // today | yesterday | all | range
  from  : '',
  to    : '',
  store : ''
})

/* ── 初期ロード ── */
onMounted(async () => {
  stores.value = await api.get('stores/').then(r => r.data)
  q.store      = stores.value[0]?.id ?? ''
  await search()                      // 起動時＝今日
})

/* ── 検索 ── */
async function search () {
  const params = buildParams()

  rows.value = await api.get('reservations/', { params }).then(r => r.data)

  const s = await api.get('sales/summary/', { params }).then(r => r.data)
  summary.today = s.today_total
  summary.month = s.month_total
}

/* ── パラメータ生成 ── */
function buildParams () {
  const today = dayjs().format('YYYY-MM-DD')
  const p     = { store: q.store }

  switch (q.period) {
    case 'today': {
      p.from = p.to = today
      break
    }
    case 'yesterday': {
      const y = dayjs().subtract(1, 'day').format('YYYY-MM-DD')
      p.from = p.to = y
      break
    }
    case 'all':
      /* 期間条件なし → そのまま */
      break
    case 'range':
      if (q.from) p.from = q.from
      if (q.to)   p.to   = q.to
      break
  }
  return p
}
</script>

<template>
<div class="container py-4">
  <!-- ① サマリー -->
  <div class="alert alert-primary d-flex justify-content-between">
    <div>本日の総売上：<strong>¥{{ (summary.today ?? 0).toLocaleString() }}</strong></div>
    <div>今月の総売上：<strong>¥{{ (summary.month ?? 0).toLocaleString() }}</strong></div>
  </div>

  <!-- ② 検索フォーム -->
  <form class="card p-3 mb-4" @submit.prevent="search">
    <div class="row g-3 align-items-end">

      <!-- 期間選択 -->
      <div class="col-md-6">
        <label class="form-label">期間</label>
        <div class="btn-group d-block">
          <input type="radio" class="btn-check" id="p-today" value="today"     v-model="q.period">
          <label class="btn btn-outline-primary" for="p-today">本日</label>

          <input type="radio" class="btn-check" id="p-yest"  value="yesterday" v-model="q.period">
          <label class="btn btn-outline-primary" for="p-yest">昨日</label>

          <input type="radio" class="btn-check" id="p-all"   value="all"       v-model="q.period">
          <label class="btn btn-outline-primary" for="p-all">全期間</label>

          <input type="radio" class="btn-check" id="p-range" value="range"     v-model="q.period">
          <label class="btn btn-outline-primary" for="p-range">期間指定</label>
        </div>

        <!-- 手入力期間 -->
        <div v-if="q.period==='range'" class="mt-2 d-flex gap-2">
          <input type="date" v-model="q.from" class="form-control">
          <span class="align-self-center">–</span>
          <input type="date" v-model="q.to"   class="form-control">
        </div>
      </div>

      <!-- 店舗 -->
      <div class="col-md-3">
        <label class="form-label">店舗</label>
        <select v-model="q.store" class="form-select">
          <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>

      <!-- ボタン -->
      <div class="col-md-3 text-end">
        <button class="btn btn-success px-5">検索</button>
      </div>
    </div>
  </form>

  <!-- ③ 一覧 -->
  <table class="table table-sm">
    <thead>
      <tr>
        <th>日付</th><th>開始</th><th>キャスト</th><th>顧客</th>
        <th class="text-end">見積</th><th class="text-end">受取</th>
        <th class="text-end">差額</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="r in rows" :key="r.id" :class="{ 'table-danger': r.discrepancy_flag }">
        <td>{{ dayjs(r.start_at).format('YYYY-MM-DD') }}</td>
        <td>{{ dayjs(r.start_at).format('HH:mm') }}</td>
        <td>{{ r.cast_names?.join(', ') }}</td>
        <td>{{ r.customer_name }}</td>

        <td class="text-end">{{ (r.expected_amount ?? 0).toLocaleString() }}</td>
        <td class="text-end">{{ (r.received_amount ?? 0).toLocaleString() }}</td>
        <td class="text-end">
          {{ ((r.received_amount ?? 0) - (r.expected_amount ?? 0)).toLocaleString() }}
        </td>
      </tr>
    </tbody>
  </table>
</div>
</template>
