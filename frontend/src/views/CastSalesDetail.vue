<!-- src/views/CastSalesDetail.vue -->
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
  fetchCastSalesDetail,   // ← CastPayout（stay_type つき）
  fetchCastItemDetails,   // ← 小計フォールバック用
  fetchCastShiftHistory
} from '@/api'

/* ---------- ルーティング ---------- */
const route = useRoute()
const router = useRouter()
const { params:{ id } } = route

/* ---------- 期間 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- データ ---------- */
const payouts = ref([])   // ギャラ行（CastPayout）
const items   = ref([])   // 明細行（小計フォールバック用）
const shifts  = ref([])   // 勤務シフト

/* ---------- 取得 ---------- */
async function load () {
  const params = { from: dateFrom.value, to: dateTo.value, limit: 1000 } // ← from/to に統一
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

const castName = computed(() =>
  payouts.value?.[0]?.cast?.stage_name ||
  route.query?.name ||
  ''
)

/* Bill.id → items[] マップ（小計フォールバック用） */
const detailMap = computed(() => {
  const m = {}
  for (const it of (items.value || [])) {
    const bid = it.bill_id
    if (!bid) continue
    ;(m[bid] ||= []).push(it)
  }
  return m
})

/* bill 小計：bill.subtotal があればそれを優先。無ければ items から合算 */
function billSubtotal(p) {
  const sub = Number(p?.bill?.subtotal) || 0
  if (sub) return sub
  const bid = p?.bill?.id
  if (!bid) return 0
  return (detailMap.value[bid] || []).reduce((s, it) => s + (Number(it.subtotal) || 0), 0)
}

/* 区分ラベル/色（stay_type 優先） */
const nomType = p => (p.stay_type === 'nom'   ? '本指名'
                   : p.stay_type === 'in'    ? '場内'
                   : p.stay_type === 'dohan' ? '同伴'
                   : 'フリー')

const badgeClass = p => (p.stay_type === 'nom'   ? 'badge bg-danger text-white'
                     : p.stay_type === 'in'    ? 'badge bg-success text-white'
                     : p.stay_type === 'dohan' ? 'badge bg-secondary text-white'
                     : 'badge bg-primary text-white')

/* 合計（ギャラ総額）*/
const totalPayout = computed(() => payouts.value.reduce((s,p)=> s + (Number(p.amount)||0), 0))

/* クリックで bill 詳細へ */
function goBill(p) {
  const bid = p?.bill?.id
  if (!bid) return
  router.push(`/bills/${bid}`)
}
</script>

<template>
  <div class="container-fluid">
    <h4 class="my-3 fw-bold text-center">
      {{ castName }}さんの売上
    </h4>

    <!-- 期間指定 -->
    <div class="d-flex align-items-end gap-2 mb-3 justify-content-end">
      <div>
        <label class="form-label mb-0">開始日</label>
        <input v-model="dateFrom" type="date" class="form-control bg-white" />
      </div>
      <div>
        <label class="form-label mb-0">終了日</label>
        <input v-model="dateTo" type="date" class="form-control bg-white" />
      </div>
      <button class="btn btn-primary mb-1" @click="load">再表示</button>
    </div>

    <!-- テーブル（子明細リストは撤去） -->
    <table class="table align-middle">
      <thead class="table-dark">
        <tr>
          <th class="text-center">卓</th>
          <th>区分</th>
          <th class="text-center">日付</th>
          <th class="text-center">時間</th>
          <th class="text-end">テーブル小計</th>
          <th class="text-end">ギャラ</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!payouts?.length">
          <td colspan="6" class="text-center text-muted">対象期間のギャラはありません</td>
        </tr>

        <tr v-for="p in payouts" :key="p.id" class="fw-bold bg-white">
          <td class="text-center">
            {{ p.bill.table_no ?? p.bill.table ?? '-' }}
          </td>
          <td>
            <span :class="badgeClass(p)" class="d-inline-flex align-items-center">
              {{ nomType(p) }}
            </span>
          </td>

          <!-- 日付/時間：クリックで /bills/:id -->
          <td class="text-center">
            <a href="#" @click.prevent="goBill(p)">
              {{ dayjs(p.bill.closed_at || p.bill.opened_at).format('YYYY/MM/DD') }}
            </a>
          </td>
          <td class="text-center">
            <a href="#" @click.prevent="goBill(p)">
              {{ dayjs(p.bill.closed_at || p.bill.opened_at).format('HH:mm') }}
            </a>
          </td>

          <td class="text-end">
            {{ yen(billSubtotal(p)) }}
          </td>
          <td class="text-end">
            {{ yen(p.amount) }}
          </td>
        </tr>
      </tbody>

      <tfoot class="fw-bold table-light" v-if="payouts?.length">
        <tr>
          <td colspan="5" class="text-end">ギャラ合計</td>
          <td class="text-end">{{ yen(totalPayout) }}</td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<style scoped>
a { text-decoration: none; }
a:hover { text-decoration: underline; }
</style>