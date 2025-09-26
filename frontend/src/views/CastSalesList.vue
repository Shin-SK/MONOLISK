<!-- src/views/CastSalesList.vue (キャスト別集計版) -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter }      from 'vue-router'
import dayjs              from 'dayjs'
import { fetchCastDailySummaries, fetchCasts } from '@/api'

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ ---------- */
const dailyRows = ref([])   // API 生レコード（日別）
const totals    = ref([])   // キャスト別集計結果
const allCasts  = ref([])

const router = useRouter()
const yen = n => `¥${(+n || 0).toLocaleString()}`

/* ---------- 集計 ---------- */
function aggregate () {
  const map = new Map()

  /* ---------- 集計（実売上があるキャスト） ---------- */
  dailyRows.value.forEach(r => {
    const id = r.cast.id
    if (!map.has(id)) {
      map.set(id, {
        cast:r.cast, champ:0, nom:0, in:0, free:0,
        comm:0, pay:0, grand:0
      })
    }
    const t = map.get(id)
    t.champ += r.sales_champ
    t.nom   += r.sales_nom
    t.in    += r.sales_in
    t.free  += r.sales_free
    t.comm  += r.total
    t.pay   += r.payroll
    t.grand  = t.comm + t.pay
  })

  /* ---------- 売上ゼロのキャストを追加 ---------- */
  allCasts.value.forEach(c => {
    if (!map.has(c.id)) {
      map.set(c.id, {
        cast:c, champ:0, nom:0, in:0, free:0,
        comm:0, pay:0, grand:0
      })
    }
  })

  totals.value = [...map.values()].sort((a,b) => b.grand - a.grand)
}


/* ---------- 取得 ---------- */
async function load () {
  const [rows, casts] = await Promise.all([
    fetchCastDailySummaries({ from: dateFrom.value, to: dateTo.value }),
    fetchCasts()
  ])
  dailyRows.value = rows
  allCasts.value  = casts
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