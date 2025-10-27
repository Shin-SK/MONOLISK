<!-- src/views/CastSalesList.vue (キャスト別集計版) -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter }      from 'vue-router'
import dayjs              from 'dayjs'
import { fetchCastDailySummaries, fetchCasts, fetchPayrollSummary } from '@/api'

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ ---------- */
const dailyRows   = ref([])   // CastDailySummary（日別の売上金額・時給）
const totals      = ref([])   // 画面に出すキャスト別集計
const allCasts    = ref([])   // 全キャスト（売上ゼロも表示用）
const paySummary  = ref([])   // fetchPayrollSummary（出来高=commission / 時給=hourly_pay）

const router = useRouter()
const yen = n => `¥${(+n || 0).toLocaleString()}`

/* ---------- 集計 ---------- */
function aggregate () {
  const map = new Map()

  // Payrollサマリ → {castId: commission/hourly} マップ
  const commByCast = new Map()
  const payByCast  = new Map()
  for (const s of (paySummary.value || [])) {
    const cid = Number(s.id) // { id, commission, hourly_pay, total, ... }
    if (!cid) continue
    commByCast.set(cid, Number(s.commission)  || 0)
    payByCast.set(cid,  Number(s.hourly_pay) || 0)
  }

  // 実売上があるキャスト（日次サマリから金額列を合算）
  for (const r of (dailyRows.value || [])) {
    const id = r.cast.id
    if (!map.has(id)) {
      map.set(id, {
        cast: r.cast, champ:0, nom:0, in:0, free:0,
        comm:0, pay:0, grand:0
      })
    }
    const t = map.get(id)
    t.champ += Number(r.sales_champ) || 0
    t.nom   += Number(r.sales_nom)   || 0
    t.in    += Number(r.sales_in)    || 0
    t.free  += Number(r.sales_free)  || 0
    // 歩合は CastPayout 合算（店舗エンジンの 20%/500 反映）
    t.comm   = commByCast.get(id) || 0
    // 時給は日次サマリ（複数日分を都度加算）
    t.pay   += Number(r.payroll) || 0
    t.grand  = t.comm + t.pay
  }

  // 売上ゼロのキャストも行を作る
  for (const c of (allCasts.value || [])) {
    if (!map.has(c.id)) {
      const comm = commByCast.get(c.id) || 0
      const pay  = payByCast.get(c.id)  || 0
      map.set(c.id, { cast:c, champ:0, nom:0, in:0, free:0, comm, pay, grand: comm + pay })
    }
  }

  totals.value = [...map.values()].sort((a,b) => b.grand - a.grand)
}

/* ---------- 取得 ---------- */
async function load () {
  const [rows, casts, sum] = await Promise.all([
    fetchCastDailySummaries({ from: dateFrom.value, to: dateTo.value }),
    fetchCasts(),
    fetchPayrollSummary({ from: dateFrom.value, to: dateTo.value })
  ])
  dailyRows.value   = Array.isArray(rows) ? rows : []
  allCasts.value    = Array.isArray(casts?.results) ? casts.results : (Array.isArray(casts) ? casts : [])
  paySummary.value  = Array.isArray(sum)  ? sum  : []
  aggregate()
}

onMounted(load)
</script>

<template>
  <div class="container-fluid mt-4">
    <!-- 期間選択 -->
    <div class="d-flex gap-1 mb-2 align-items-center flex-wrap">
      <div class="">
        <input
          v-model="dateFrom"
          type="date"
          class="form-control form-control-sm"
        >
      </div>
      <div class="d-flex align-items-center justify-content-center">〜</div>
      <div class="">
        <input
          v-model="dateTo"
          type="date"
          class="form-control form-control-sm"
        >
      </div>
      <div class="">
        <button
          class="btn btn-secondary btn-sm"
          @click="load"
          style="white-space: nowrap;"
        >
          再表示
        </button>
      </div>
    </div>

    <div class="table-responsive">

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
            <th class="text-end">
              合計
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="t in totals"
            :key="t.cast.id"
            style="cursor:pointer"
            @click="
              router.push({
                name: 'cast-sales-detail',
                params: { id: t.cast.id },              // 必須パラメータ
                query:  { from: dateFrom, to: dateTo }  // 期間も持たせたい場合（省略可）
              })
            "
          >
            <td>{{ t.cast.stage_name }}</td>
            <td>{{ yen(t.champ) }}</td>
            <td>{{ yen(t.nom) }}</td>
            <td>{{ yen(t.in) }}</td>
            <td>{{ yen(t.free) }}</td>
            <td class="fw-bold">
              {{ yen(t.comm) }}
            </td>
            <td>{{ yen(t.pay) }}</td>
            <td class="text-end fw-bold">
              {{ yen(t.grand) }}
            </td>
          </tr>
        </tbody>
      </table>

    </div>

  </div>
</template>


<style scoped lang="scss">

  input,select{
    background-color: white;
  }

 table{
  td,th{
    white-space: nowrap;
  }
 }

</style>