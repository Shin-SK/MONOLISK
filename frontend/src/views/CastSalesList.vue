<!-- src/views/CastSalesList.vue (キャスト別集計版) -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter }      from 'vue-router'
import dayjs              from 'dayjs'
import { fetchCastDailySummaries } from '@/api'

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ ---------- */
const dailyRows = ref([])   // API 生レコード（日別）
const totals    = ref([])   // キャスト別集計結果

const router = useRouter()
const yen = n => `¥${(+n || 0).toLocaleString()}`

/* ---------- 集計 ---------- */
function aggregate () {
  const map = new Map()
  dailyRows.value.forEach(r => {
    const id = r.cast.id
    if (!map.has(id)) {
      map.set(id, {
        cast  : r.cast,
        champ : 0,
        nom   : 0,
        in    : 0,
        free  : 0,
        comm  : 0,  // 歩合小計
        pay   : 0,  // 時給小計
      })
    }
    const t = map.get(id)
    t.champ += r.sales_champ
    t.nom   += r.sales_nom
    t.in    += r.sales_in
    t.free  += r.sales_free
    t.comm  += r.total
    t.pay   += r.payroll
  })
  totals.value = [...map.values()].map(t => ({ ...t, grand: t.comm + t.pay }))
    .sort((a,b) => b.grand - a.grand)
}

/* ---------- 取得 ---------- */
async function load () {
  dailyRows.value = await fetchCastDailySummaries({ from: dateFrom.value, to: dateTo.value })
  aggregate()
}

onMounted(load)
</script>

<template>
  <div class="container-fluid mt-4">
    <!-- 期間選択 -->
    <div class="d-flex align-items-center gap-3 mb-3">
      <div>
        <input type="date" v-model="dateFrom" class="form-control" />
      </div>
      <div>〜</div>
      <div>
        <input type="date" v-model="dateTo" class="form-control" />
      </div>
      <button class="btn btn-primary mb-1" @click="load">再表示</button>
    </div>

    <!-- 一覧 (キャスト1行) -->
    <table class="table table-striped table-hover">
      <thead class="table-dark">
        <tr>
          <th>キャスト</th>
          <th>シャンパン</th>
          <th>本指名</th>
          <th>場内</th>
          <th>フリー</th>
          <th>歩合小計</th>
          <th>時給小計</th>
          <th class="text-end">合計</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in totals" :key="t.cast.id"
            @click="router.push(`/cast-sales/${t.cast.id}`)"
            style="cursor:pointer">
          <td>{{ t.cast.stage_name }}</td>
          <td>{{ yen(t.champ) }}</td>
          <td>{{ yen(t.nom) }}</td>
          <td>{{ yen(t.in) }}</td>
          <td>{{ yen(t.free) }}</td>
          <td class="fw-bold">{{ yen(t.comm) }}</td>
          <td>{{ yen(t.pay) }}</td>
          <td class="text-end fw-bold">{{ yen(t.grand) }}</td>
        </tr>
        <tr v-if="!totals.length">
          <td colspan="8" class="text-center text-muted">データがありません</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
