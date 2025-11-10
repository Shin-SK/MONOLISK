<!-- src/views/owner/OwnerDashboard.vue -->
<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import dayjs from 'dayjs'
import { yen } from '@/utils/money'
import {
  getBillDailyPL, getBillMonthlyPL, getBillYearlyPL,
  fetchCastShifts, fetchCastRankings, fetchBillItems, 
} from '@/api'
import { getStoreId } from '@/auth'
import SalesTrendLine from '@/components/charts/SalesTrendLine.vue'
import SalesMixPie   from '@/components/charts/SalesMixPie.vue'
import CastRankBar   from '@/components/charts/CastRankBar.vue'

const storeId = getStoreId()
const loading = ref(true)
const err = ref('')

/* ── KPI ── */
const summary = ref({ today:{}, month:{}, year:{} })

const trendRef = ref(null)   // ← 追加
const mixRef   = ref(null)   // ← 追加
const chartsReady = ref(false)
const mixRows = ref([])

/* ── グラフ用 ── */
const days = ref([])                     // [{ date:'YYYY-MM-DD', sales:Number }]
const monthlyTotal = ref({ cash:0, card:0 })
const rankRows = ref([])                 // [{ stage_name, revenue }]

/* ── UI ── */
const tab = ref('suii')
const rankPeriod = ref('month')

const pct = v => (v===0||v==null) ? '0%' : `${v>0?'+':''}${Math.round(v)}%`
const num = v => Number.isFinite(+v) ? +v : 0

async function loadKpis(){
  const today = dayjs().format('YYYY-MM-DD')
  const prev1 = dayjs(today).subtract(1,'day').format('YYYY-MM-DD')
  const prev7 = dayjs(today).subtract(7,'day').format('YYYY-MM-DD')

  const [d0, d1, d7] = await Promise.all([
    getBillDailyPL(today, storeId),
    getBillDailyPL(prev1, storeId),
    getBillDailyPL(prev7, storeId),
  ])
  const s0 = num(d0.sales_total ?? (num(d0.sales_cash)+num(d0.sales_card)))
  const s1 = num(d1?.sales_total ?? (num(d1?.sales_cash)+num(d1?.sales_card)))
  const s7 = num(d7?.sales_total ?? (num(d7?.sales_cash)+num(d7?.sales_card)))

  let working = 0
  try {
    const shifts = await fetchCastShifts({ date: today })
    working = Array.isArray(shifts) ? shifts.filter(x => x.clock_in && !x.clock_out).length : 0
  } catch {}

  summary.value.today = {
    sales: s0,
    prev_day_pct: s1 ? ((s0 - s1)/s1)*100 : 0,
    prev_weekday_pct: s7 ? ((s0 - s7)/s7)*100 : 0,
    sets: num(d0.guest_count),                 // 暫定：来客組数を流用
    avg_unit_price: num(d0.avg_spend),
    working_casts: working,
    avg_sales_per_cast: working ? s0/working : 0,
  }

  const ym = today.slice(0,7)
  const m = await getBillMonthlyPL(ym)
  summary.value.month = { sales: num(m?.monthly_total?.sales_total), target_pct: null }

  const y = await getBillYearlyPL(dayjs().year())
  summary.value.year = { sales: num(y?.totals?.sales_total) }
}

async function loadTrendAndMix(){
  const ym = dayjs().format('YYYY-MM')
  const { days: d, monthly_total } = await getBillMonthlyPL(ym)
  days.value = (d||[]).map(x => ({
    date: x.date,
    sales: num(x.sales_total ?? (num(x.sales_cash)+num(x.sales_card)))
  }))

  // 当月の BillItem を取得 → カテゴリ(show_in_menu=True)で集計
  const from = dayjs().startOf('month').format('YYYY-MM-DD')
  const to   = dayjs().endOf('month').format('YYYY-MM-DD')
  const items = await fetchBillItems({ from, to })
  const map = new Map()
  for (const it of (items || [])) {
    const cat = it.category
    if (!cat || !cat.show_in_menu) continue
    const key = cat.code
    const cur = map.get(key) || { name: cat.name, value: 0 }
    cur.value += Number(it.subtotal) || 0
    map.set(key, cur)
  }
  mixRows.value = Array.from(map.values()).sort((a,b)=>b.value-a.value)

  monthlyTotal.value = {
    cash: num(monthly_total?.sales_cash),
    card: num(monthly_total?.sales_card),
  }
}

const trendLabels = computed(() => (days.value ?? []).map(x => x.date?.slice(5) ?? ''))
const trendValues = computed(() => (days.value ?? []).map(x => Number(x.sales) || 0))
const mixItems = computed(() => mixRows.value)

function periodRange(p='month'){
  const t = dayjs()
  if (p==='today') return { from: t.format('YYYY-MM-DD'), to: t.format('YYYY-MM-DD') }
  if (p==='year')  return { from: t.startOf('year').format('YYYY-MM-DD'),  to: t.endOf('year').format('YYYY-MM-DD') }
  return { from: t.startOf('month').format('YYYY-MM-DD'), to: t.endOf('month').format('YYYY-MM-DD') }
}

async function loadRanks(){
  const { from, to } = periodRange(rankPeriod.value)
  try {
    const rows = await fetchCastRankings({ from, to })
    rankRows.value = (rows||[]).map(r => ({
      stage_name: r.stage_name ?? r.name ?? `CAST-${r.cast_id ?? ''}`,
      revenue:    num(r.revenue ?? r.sales ?? 0),
    }))
  } catch { rankRows.value = [] }
}

onMounted(async () => {
  try {
    await Promise.all([loadKpis(), loadTrendAndMix(), loadRanks()])
  } catch(e){ err.value = e?.message || 'load error' }
  finally { 
    loading.value = false
    chartsReady.value = true 
    await nextTick()
    if (tab.value==='suii')   trendRef.value?.resize()
  }
})
watch(rankPeriod, loadRanks)
watch(tab, async (t) => {    // ← 追加：タブ切替後に強制resize
  await nextTick()
  if (t==='suii')   trendRef.value?.resize()
  if (t==='kousei') mixRef.value?.resize()
})

/* 派生 */
const kpiToday = computed(() => summary.value.today || {})
const kpiMonth = computed(() => summary.value.month || {})
const kpiYear  = computed(() => summary.value.year  || {})
</script>




<template>
  <div class="container owner-dashboard mt-3">
    <div v-if="loading">Loading...</div>
    <div v-else>
      <div v-if="err" class="text-danger small">{{ err }}</div>

      <div class="sales d-flex flex-column gap-3">
        <div class="today box">
          <div class="item item-main"><span class="fw-bold">今日の売上</span><span class="fs-1 fw-bold">{{ yen(kpiToday.sales) }}</span></div>
            <div class="mini-wrap d-flex overflow-auto flex-nowrap">
              <div class="item mini"><span class="badge bg-secondary">前日比</span><span class="fs-3">{{ pct(kpiToday.prev_day_pct) }}</span></div>
              <div class="item mini"><span class="badge bg-secondary">先週同曜比</span><span class="fs-3">{{ pct(kpiToday.prev_weekday_pct) }}</span></div>
              <div class="item mini"><span class="badge bg-secondary">本数（セット数）</span><span class="fs-3">{{ kpiToday.sets ?? 0 }}</span></div>
              <div class="item mini"><span class="badge bg-secondary">平均単価（客単価）</span><span class="fs-3">{{ yen(kpiToday.avg_unit_price) }}</span></div>
              <div class="item mini"><span class="badge bg-secondary">稼働キャスト数（本日出勤）</span><span class="fs-3">{{ kpiToday.working_casts ?? 0 }}</span></div>
              <div class="item mini"><span class="badge bg-secondary">平均売上/キャスト</span><span class="fs-3">{{ yen(kpiToday.avg_sales_per_cast) }}</span></div>
            </div>
        </div>

        <div class="d-flex gap-3">
          <div class="month box">
            <div class="item item-main"><span class="fw-bold">今月の売上</span><span class="fs-1 fw-bold">{{ yen(kpiMonth.sales) }}</span></div>
            <!-- <div class="item mini"><span class="badge bg-secondary">目標対比</span><span class="fs-3">{{ pct(kpiMonth.target_pct) }}</span></div> -->
          </div>

          <div class="year box">
            <div class="item item-main"><span class="fw-bold">今年の売上</span><span class="fs-1 fw-bold">{{ yen(kpiYear.sales) }}</span></div>
          </div>
        </div>

      </div>

      <div class="sales-transition mt-5" v-if="chartsReady">
        <div class="nav nav-pills d-flex gap-2 mb-2">
          <button class="nav-link" :class="{active: tab==='suii'}" @click="tab='suii'">売上推移</button>
          <button class="nav-link" :class="{active: tab==='kousei'}" @click="tab='kousei'">売上構成</button>
          <button class="nav-link" :class="{active: tab==='cast-rank'}" @click="tab='cast-rank'">キャスト別売上</button>
        </div>

        <div v-if="tab==='suii'" class="chart-box">
          <SalesTrendLine ref="trendRef" :labels="trendLabels" :values="trendValues" height="320px" />
        </div>

        <div v-else-if="tab==='kousei'" class="chart-box">
          <SalesMixPie ref="mixRef" :items="mixItems" title="支払別構成（当月）" height="300px" />
        </div>

        <div v-else>
          <div class="d-flex align-items-center gap-2 mb-2">
            <span>期間</span>
            <select v-model="rankPeriod" class="form-select form-select-sm w-auto">
              <option value="today">今日</option>
              <option value="month">今月</option>
              <option value="year">年</option>
            </select>
          </div>
          <CastRankBar :rows="rankRows" height="360px" />
          <!-- or 既存のRankingBlockを使う場合
          <RankingBlock :rows="rankRows" label="キャスト別売上" />
          -->
        </div>
      </div>
      
    </div>
  </div>
</template>


<style scoped>
.chart-box{ width:100%; min-height:320px; }
.sales-transition { min-width: 0; }
</style>