<!-- src/views/CastSalesList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter }      from 'vue-router'
import dayjs              from 'dayjs'
import { fetchCastDailySummaries } from '@/api'

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ ---------- */
const casts  = ref([])                // /cast‑daily‑summaries の結果
const router = useRouter()

/* ---------- util ---------- */
const yen = n => `¥${(+n || 0).toLocaleString()}`

/* ---------- 取得 ---------- */
async function load () {
  casts.value = await fetchCastDailySummaries({
    from : dateFrom.value,
    to   : dateTo.value,
  })
}

onMounted(load)
</script>

<template>
  <div class="container-fluid mt-4">
    <h2 class="mb-3">キャスト売上一覧</h2>

    <!-- 期間選択 -->
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

    <!-- 一覧 -->
    <table class="table table-striped">
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
        <tr v-for="c in casts" :key="c.id"
            @click="router.push(`/cast-sales/${c.cast.id}`)"
            style="cursor:pointer">
          <!-- ☆ 新しい JSON 構造に合わせて stage_name 取得方法を変更 ------- -->
          <td>{{ c.cast.stage_name }}</td>

          <td>{{ yen(c.sales_champ) }}</td>
          <td>{{ yen(c.sales_nom) }}</td>
          <td>{{ yen(c.sales_in) }}</td>
          <td>{{ yen(c.sales_free) }}</td>

          <!-- 歩合小計（= total フィールド） -->
          <td class="fw-bold">{{ yen(c.total) }}</td>

          <!-- 時給小計（= payroll フィールド） -->
          <td>{{ yen(c.payroll) }}</td>

          <!-- 歩合 + 時給 合算 -->
          <td class="text-end fw-bold">
            {{ yen((c.total || 0) + (c.payroll || 0)) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
