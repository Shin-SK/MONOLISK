<!-- src/views/CastSalesList.vue (キャスト別集計版) -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter }      from 'vue-router'
import dayjs              from 'dayjs'
import {
  fetchCastDailySummaries,   // ← champ 売上（sales_champ）用
  fetchCasts,
  fetchPayrollSummary,       // ← 時給合計
  listCastPayouts         // ← 期間の CastPayout 明細（stay_type 付き）
} from '@/api'

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ ---------- */
const dailyRows   = ref([])   // CastDailySummary（日毎）
const totals      = ref([])   // 画面に出すキャスト別集計
const allCasts    = ref([])   // 全キャスト（ゼロも表示）
const paySummary  = ref([])   // {id, hourly_pay, commission, ...}
const payouts     = ref([])   // CastPayout（stay_type 付き）

const router = useRouter()
const yen = n => `¥${(+n || 0).toLocaleString()}`

/* ---------- 集計 ---------- */
function aggregate () {
  const map = new Map()

  // 1) champ 売上（CastDailySummary）
  const champByCast = new Map()
  for (const r of (dailyRows.value || [])) {
    const cid = r.cast?.id
    if (!cid) continue
    champByCast.set(cid, (champByCast.get(cid) || 0) + (Number(r.sales_champ) || 0))
  }

  // 2) 歩合内訳（CastPayout の stay_type 別）
  const nomByCast = new Map()
  const inByCast  = new Map()
  const freeByCast= new Map()
  for (const p of (payouts.value || [])) {
    const cid = (typeof p.cast === 'object' ? p.cast?.id : p.cast) ?? p.cast_id
    if (!cid) continue
    const amt = Number(p.amount) || 0
    const st  = p.stay_type || (p.bill_item?.is_inhouse ? 'in' : 'free')
    if (st === 'nom')      nomByCast.set(cid,  (nomByCast.get(cid)   || 0) + amt)
    else if (st === 'in')  inByCast.set(cid,   (inByCast.get(cid)    || 0) + amt)
    else                   freeByCast.set(cid, (freeByCast.get(cid)  || 0) + amt)
  }

  // 3) 時給（PayrollSummary）
  const payByCast  = new Map()
  for (const s of (paySummary.value || [])) {
    const cid = Number(s.id)
    if (!cid) continue
    payByCast.set(cid, Number(s.hourly_pay) || 0)
  }

  // 4) 行を作る（ゼロも表示）
  const every = new Set([
    ...Array.from(champByCast.keys()),
    ...Array.from(nomByCast.keys()),
    ...Array.from(inByCast.keys()),
    ...Array.from(freeByCast.keys()),
    ...Array.from(payByCast.keys()),
    ...allCasts.value.map(c => c.id),
  ])

  for (const cid of every) {
    const cast = (allCasts.value || []).find(c => c.id === cid) || { id: cid, stage_name: `#${cid}` }
    const champ = champByCast.get(cid)   || 0
    const nom   = nomByCast.get(cid)     || 0
    const inn   = inByCast.get(cid)      || 0
    const free  = freeByCast.get(cid)    || 0
    const pay   = payByCast.get(cid)     || 0
    const comm  = nom + inn + free

    map.set(cid, {
      cast, champ,
      nom, in: inn, free,
      comm,            // 歩合小計 = 3区分の合計
      pay,
      grand: comm + pay,
    })
  }

  totals.value = [...map.values()].sort((a,b) => b.grand - a.grand)
}

/* ---------- 取得 ---------- */
async function load () {
  const [rows, casts, sum, pays] = await Promise.all([
    fetchCastDailySummaries({ from: dateFrom.value, to: dateTo.value }),
    fetchCasts(),
    fetchPayrollSummary({ from: dateFrom.value, to: dateTo.value }),
    listCastPayouts({ from: dateFrom.value, to: dateTo.value, limit: 10000 })   // stay_type 付きで取得
  ])
  dailyRows.value   = Array.isArray(rows) ? rows : []
  allCasts.value    = Array.isArray(casts?.results) ? casts.results : (Array.isArray(casts) ? casts : [])
  paySummary.value  = Array.isArray(sum)  ? sum  : []
  payouts.value     = Array.isArray(pays) ? pays : []
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