<!-- src/views/CastSalesDetail.vue (date/time 分離＋バッジ付き) -->
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
import {
  fetchCastSalesDetail,
  fetchCastItemDetails,
  fetchCastShiftHistory
} from '@/api'

/* ---------- ルーティング ---------- */
const { params:{ id } } = useRoute()

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ ---------- */
const payouts = ref([])   // ギャラ行
const items   = ref([])   // 明細行
const shifts  = ref([])   // 勤務シフト

/* ---------- 取得 ---------- */
async function load () {
  const params = {
    date_from: dateFrom.value,
    date_to:   dateTo.value
  }
  ;[payouts.value, items.value, shifts.value] = await Promise.all([
    fetchCastSalesDetail(id, params),
    fetchCastItemDetails(id, params),
    fetchCastShiftHistory(id, params)
  ])
}

onMounted(load)
watch([dateFrom, dateTo], load)

/* ---------- util & 集計 ---------- */
const yen = n => `¥${(+n || 0).toLocaleString()}`
const castName = computed(() => payouts.value[0]?.cast?.stage_name || '')

const totalPayout = computed(() => payouts.value.reduce((s,p)=>s+p.amount,0))
const payrollSum  = computed(() => shifts.value.reduce((s,sh)=>s+(sh.payroll_amount||0),0))

/* 指名区分とバッジ */
const nomType = p => {
  if (!p.bill_item)           return '本指名'
  if (p.bill_item.is_inhouse) return '場内'
  return 'フリー'
}
const badgeClass = p => {
  if (!p.bill_item)           return 'badge bg-danger text-white'
  if (p.bill_item.is_inhouse) return 'badge bg-success text-white'
  return 'badge bg-primary text-white'
}

/* Bill.id → items[] マップ */
const detailMap = computed(() => {
  const m = {}
  items.value.forEach(it => { (m[it.bill_id] ??= []).push(it) })
  return m
})
</script>

<template>
  <div class="container-fluid">
    <h4 class="my-3 fw-bold text-center">
      {{ castName }}さんの売上
    </h4>
    <div class="d-flex justify-content-between align-items-end">


      <!-- 期間指定 -->
      <div class="d-flex align-items-end gap-2 mb-1 justify-content-end w-100">
        <div>
          <label class="form-label mb-0">開始日</label>
          <input
            v-model="dateFrom"
            type="date"
            class="form-control bg-white"
          >
        </div>
        <div>
          <label class="form-label mb-0">終了日</label>
          <input
            v-model="dateTo"
            type="date"
            class="form-control bg-white"
          >
        </div>
        <button
          class="btn btn-primary mb-1"
          @click="load"
        >
          再表示
        </button>
      </div>
    </div>

    <!-- テーブル -->
    <table class="table align-middle">
      <thead class="table-dark">
        <tr>
          <th class="text-center">
            <IconPinned />
          </th>
          <th />
          <th />
          <th />
          <th class="text-end">
            テーブル小計
          </th>
          <th class="text-end">
            ギャラ
          </th>
        </tr>
      </thead>
      <tbody>
        <template
          v-for="p in payouts"
          :key="p.id"
        >
          <!-- 親行 -->
          <tr class="fw-bold bg-white">
            <td class="text-center">
              {{ p.bill.table_no ?? p.bill.table }}
            </td>
            <td />
            <td>
              <div class="d-flex gap-3">
                <span
                  :class="badgeClass(p)"
                  class="d-flex align-items-center"
                >{{ nomType(p) }}</span>
                <span>{{ dayjs(p.bill.opened_at).format('YYYY/MM/DD') }}</span>
                <span>{{ dayjs(p.bill.opened_at).format('HH:mm') }}</span>
              </div>
            </td>
            <td />
            <td class="text-end">
              {{ yen(p.bill.subtotal) }}
            </td>
            <td class="text-end">
              {{ yen(p.amount) }}
            </td>
          </tr>

          <!-- 子行 (= アイテム明細) -->
          <tr
            v-for="it in detailMap[p.bill.id] ?? []"
            :key="it.id"
            class="bg-light small"
          >
            <td colspan="3" />
            <td class="text-end">
              {{ it.name }}×{{ it.qty }}
            </td>
            <td class="text-end">
              {{ yen(it.subtotal) }}
            </td>
            <td class="text-end">
              {{ yen(it.amount) }}
            </td>
          </tr>
        </template>
      </tbody>
      <tfoot class="fw-bold table-light">
        <tr>
          <td
            colspan="5"
            class="text-end"
          >
            売上合計
          </td>
          <td class="text-end">
            {{ yen(payouts.reduce((sum, p) => sum + p.bill.subtotal, 0)) }}
          </td>
        </tr>
        <tr>
          <td
            colspan="5"
            class="text-end"
          >
            総ギャラ合計
          </td>
          <td class="text-end">
            {{ yen(totalPayout) }}
          </td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>
