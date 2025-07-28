<!-- CastSalesList.vue  -->
<script setup>
import { ref, onMounted } from 'vue'
import { fetchCastSalesSummary } from '@/api'
import dayjs from 'dayjs'

/* --- reactive state -------------------------------------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))
const casts    = ref([])

/* --- util ------------------------------------------------- */
const yen = n => `¥${(+n || 0).toLocaleString()}`

/* --- fetch ----------------------------------------------- */
async function load () {
  casts.value = await fetchCastSalesSummary({
    from : dateFrom.value,
    to   : dateTo.value,
  })
}

onMounted(load)
</script>

<template>
  <div class="container-fluid mt-4">
    <h2 class="mb-3">キャスト売上一覧</h2>

    <!-- ▼ 期間指定 -->
    <div class="d-flex align-items-end gap-2 mb-3">
      <div>
        <label class="form-label">開始日</label>
        <input type="date" v-model="dateFrom" class="form-control" />
      </div>
      <div>
        <label class="form-label">終了日</label>
        <input type="date" v-model="dateTo" class="form-control" />
      </div>
      <button class="btn btn-primary mb-1" @click="load">再表示</button>
    </div>

    <!-- ▼ 一覧 -->
    <table class="table table-striped">
      <thead class="table-dark">
        <tr>
          <th>キャスト</th>
          <th>シャンパン</th>
          <th class="text-end">本指名</th>
          <th class="text-end">場内</th>
          <th class="text-end">フリー</th>
          <th class="text-end">合計</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in casts" :key="c.cast_id">
          <td>{{ c.stage_name }}</td>
          <td>{{ yen(c.sales_champ) }}</td>
          <td class="text-end">{{ yen(c.sales_nom) }}</td>
          <td class="text-end">{{ yen(c.sales_in) }}</td>
          <td class="text-end">{{ yen(c.sales_free) }}</td>
          <td class="text-end fw-bold">{{ yen(c.total) }}</td>
          <td class="text-end">
            <router-link :to="`/cast-sales/${c.cast_id}`"
                         class="btn btn-sm btn-outline-primary">
              詳細
            </router-link>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
