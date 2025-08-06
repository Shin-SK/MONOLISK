<!-- CastSales.vue – キャスト売上一覧（当日／当週／当月） -->
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import dayjs                               from 'dayjs'
import 'dayjs/locale/ja'
import isoWeek                             from 'dayjs/plugin/isoWeek'
import { api }                             from '@/api'

dayjs.locale('ja')
dayjs.extend(isoWeek)

/* ---------- タブ切替 ---------- */
const period = ref('month')     // 'day' | 'week' | 'month'

/* ---------- 日付レンジ ---------- */
function currentRange(p){
  const d = dayjs()
  if (p === 'day')   return { from:d.startOf('day'),   to:d.endOf('day')   }
  if (p === 'week')  return { from:d.startOf('isoWeek'), to:d.endOf('isoWeek') }
  return { from:d.startOf('month'), to:d.endOf('month') }
}

/* ---------- ステート ---------- */
const loading = ref(false)
const rows    = ref([])       // API からの予約配列
const error   = ref(null)

/* ---------- データ取得 ---------- */
async function load(){
  loading.value = true
  error.value   = null
  const { from, to } = currentRange(period.value)
  try{
    const { data } = await api.get('reservations/mine-cast', {
      params:{
        from: from.format('YYYY-MM-DD'),
        to:   to.format('YYYY-MM-DD')
      }
    })
    rows.value = data
  }catch(e){
    error.value = e
  }finally{
    loading.value = false
  }
}
onMounted(load)
watch(period, load)

/* ---------- 集計 ---------- */
const total = computed(()=>{
  return rows.value.reduce((sum,r)=>
    sum + (r.received_amount ?? 0), 0)
})

/* 日別にまとめてテーブル表示用 */
const dailyMap = computed(()=>{
  const map = new Map()
  rows.value.forEach(r=>{
    const key = r.start_at.slice(0,10)
    const cur = map.get(key) || 0
    map.set(key, cur + (r.received_amount ?? 0))
  })
  /* 日付昇順 */
  return Array.from(map.entries()).sort(([a],[b])=> a.localeCompare(b))
})
</script>

<template>
  <div class="container py-4">
    <h1 class="h4 mb-3">
      売上（キャスト）
    </h1>

    <!-- ▼ 期間タブ -->
    <ul class="nav nav-pills mb-3">
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{active:period==='day'}"
          @click="period='day'"
        >
          今日
        </button>
      </li>
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{active:period==='week'}"
          @click="period='week'"
        >
          今週
        </button>
      </li>
      <li class="nav-item">
        <button
          class="nav-link"
          :class="{active:period==='month'}"
          @click="period='month'"
        >
          今月
        </button>
      </li>
    </ul>

    <div
      v-if="error"
      class="alert alert-danger"
    >
      通信エラー
    </div>
    <div v-else-if="loading">
      読み込み中…
    </div>

    <!-- ▼ 集計 -->
    <div v-else>
      <h2 class="h5">
        合計&nbsp;{{ total.toLocaleString() }} 円
      </h2>

      <table class="table table-sm mt-3">
        <thead>
          <tr>
            <th style="width:40%">
              日付
            </th><th>受取金額</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="[d,amt] in dailyMap"
            :key="d"
          >
            <td>{{ dayjs(d).format('M/D（ddd）') }}</td>
            <td>{{ amt.toLocaleString() }} 円</td>
          </tr>
          <tr v-if="!dailyMap.length">
            <td
              colspan="2"
              class="text-center text-muted"
            >
              データなし
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
