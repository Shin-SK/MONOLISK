<!-- src/views/OwnerDashboard.vue -->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
import {
  getBillDailyPL,
  getBillDailyPLForStore,
  fetchBills,
  fetchCastShifts,
  fetchStaffShifts,
} from '@/api'
import MiniTip from '@/components/MiniTip.vue'
import Avatar from '@/components/Avatar.vue'
import { useUser } from '@/stores/useUser'
import { useProfile } from '@/composables/useProfile'
import PLPage from '../PLPage.vue'
import BillList from '../BillList.vue'

const route = useRoute()
const user = useUser()
const { avatarURL } = useProfile()

const userName = computed(() => {
  return user.me?.username || user.me?.email || 'ユーザー'
})

/* ----------------- 店舗選択（オーナー用） ----------------- */
const selectedStoreIds = ref([])

const availableStores = computed(() => {
  const mems = Array.isArray(user.me?.memberships) ? user.me.memberships : []
  return mems.map(m => ({ id: m.store_id, name: m.store_name })).filter(s => s.id != null)
})

const showStoreSelector = computed(() => {
  const role = user.me?.current_role || ''
  return (role === 'owner' || role === 'superuser') && availableStores.value.length > 1
})

function toggleStore(storeId) {
  const idx = selectedStoreIds.value.indexOf(storeId)
  if (idx >= 0) {
    if (selectedStoreIds.value.length > 1) {
      selectedStoreIds.value.splice(idx, 1)
    }
  } else {
    selectedStoreIds.value.push(storeId)
  }
}

function isStoreSelected(storeId) {
  return selectedStoreIds.value.includes(storeId)
}

// billsタブ用：単一選択
function selectStoreForBills(storeId) {
  selectedStoreIds.value = [storeId]
}

const showOpenTip = ref(false)
const showDutyTip = ref(false)

/* ----------------- タブ管理 ----------------- */
const activeTab = ref('home') // 'home', 'bills', 'download'
const homeSubTab = ref('day') // 'day', 'month', 'year'

function switchTab(tabId) {
  activeTab.value = tabId
}

function switchHomeTab(subTabId) {
  homeSubTab.value = subTabId
}

/* ----------------- 日付（単日） ----------------- */
const date = ref(dayjs().format('YYYY-MM-DD'))

/* ----------------- 状態 ----------------- */
const loading = ref(false)
const errorMsg = ref('')

const kpi = ref({
  sales_total: 0,
  sales_cash: 0,
  sales_card: 0,
  visitors: 0,
  open_count: 0,
  unsettled_count: 0,
  cast_on_duty: 0,
  staff_on_duty: 0,
})

const billsToday = ref([])   // 今日の伝票（最小表示用）

/* ----------------- ユーティリティ ----------------- */
const asId = v => (v && typeof v === 'object') ? v.id : v
const fmtYen = n => `¥${(Number(n)||0).toLocaleString()}`
const fmtTime = t => t ? dayjs(t).format('HH:mm') : '-'

/* ----------------- ロード ----------------- */
async function loadAll(){
  loading.value = true
  errorMsg.value = ''
  try{
    const d = date.value

    // 1) PL（売上）- キャッシュ無効化
    //    オーナーは全所属店舗の合算。その他は現在店舗のみ。
    let pl
    const mems = Array.isArray(user.me?.memberships) ? user.me.memberships : []
    const storeIds = mems.map(m => m.store_id).filter(id => id != null)
    if (storeIds.length > 1) {
      const list = await Promise.all(
        storeIds.map(sid => getBillDailyPLForStore(d, sid, { cache:false, meta:{ silent:true } }).catch(()=>({})))
      )
      const sum = (arr, key) => arr.reduce((a,b)=> a + (Number(b?.[key])||0), 0)
      pl = {
        sales_total : sum(list, 'sales_total'),
        sales_cash  : sum(list, 'sales_cash'),
        sales_card  : sum(list, 'sales_card'),
      }
    } else {
      pl = await getBillDailyPL(d, { cache: false })
    }

    // 2) 伝票（クライアントで当日抽出）- キャッシュ無効化
    const allBills = await fetchBills({ ordering: '-opened_at' }, { cache: false }).catch(()=>[])
    const onlyToday = (Array.isArray(allBills?.results) ? allBills.results : allBills || [])
      .filter(b => b.opened_at && dayjs(b.opened_at).isSame(d, 'day'))
    billsToday.value = onlyToday

    // 来店数：当日の全伝票の “customers” をユニーク化
    const custSet = new Set()
    for (const b of onlyToday) {
      const arr = Array.isArray(b.customers) ? b.customers : []
      for (const c of arr) custSet.add(asId(c))
    }

    // オープン中／未決済
    const openCnt      = onlyToday.filter(b => !b.closed_at).length
    const unsettledCnt = onlyToday.filter(b => {
      const st = (b.settled_total ?? b.grand_total) || 0
      const pt = b.paid_total || 0
      return b.closed_at && pt < st
    }).length

// 3) 出勤状況（キャスト／スタッフ）- キャッシュ無効化
const [castShiftsRaw, staffShiftsRaw] = await Promise.all([
  fetchCastShifts({ from: d, to: d }, { cache: false }).catch(() => []),
  fetchStaffShifts({ time_min: `${d}T00:00:00`, time_max: `${d}T23:59:59` }, { cache: false }).catch(() => []),
])

const dayStart = dayjs(`${d}T00:00:00`)
const dayEnd   = dayjs(`${d}T23:59:59`)

// 「当日打刻のみ」＋「人物でユニーク」に絞る
const isClockInToday = (s) => {
  if (!s?.clock_in) return false
  const ci = dayjs(s.clock_in)
  return ci.isValid() && ci.isSame(dayStart, 'day')
}
const uniqCountBy = (arr, getPersonId) => {
  const seen = new Set()
  for (const s of arr) {
    const pid = getPersonId(s)
    if (pid != null) seen.add(String(pid))
  }
  return seen.size
}

// キャスト
const castShiftsToday = (Array.isArray(castShiftsRaw) ? castShiftsRaw : []).filter(isClockInToday)
// 「退勤済みでも当日ならOK」or「未退勤（勤務中）」のどちらも当日実績として扱う
const castOn = uniqCountBy(castShiftsToday, s => s.cast?.id ?? s.cast_id)

// スタッフ（構造が cast と同様だと仮定）
const staffShiftsToday = (Array.isArray(staffShiftsRaw) ? staffShiftsRaw : []).filter(isClockInToday)
const staffOn = uniqCountBy(staffShiftsToday, s => s.staff?.id ?? s.staff_id)

kpi.value = {
  sales_total : pl.sales_total || 0,
  sales_cash  : pl.sales_cash  || 0,
  sales_card  : pl.sales_card  || 0,
  visitors    : custSet.size,
  open_count  : openCnt,
  unsettled_count: unsettledCnt,
  cast_on_duty: castOn,
  staff_on_duty: staffOn,
}

  }catch(e){
    console.warn(e)
    errorMsg.value = '読み込みに失敗しました'
  }finally{
    loading.value = false
  }
}

onMounted(() => {
  // 店舗初期化：全店舗選択
  if (availableStores.value.length) {
    selectedStoreIds.value = availableStores.value.map(s => s.id)
  }
  // クエリパラメータからタブを復元
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
  loadAll()
})

watch(date, loadAll)

// クエリパラメータ変更でタブ切替
watch(() => route.query.tab, (newTab) => {
  if (newTab && newTab !== activeTab.value) {
    activeTab.value = newTab
  }
})

/* ----------------- CSV（フロント生成） ----------------- */
function csvEscape(v){
  const s = String(v ?? '')
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}
function downloadCsv(filename, headers, rows){
  const lines = []
  lines.push(headers.map(csvEscape).join(','))
  for (const r of rows) lines.push(headers.map(h => csvEscape(r[h])).join(','))
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function downloadBillsCsv(){
  const headers = [
    'id','table_no','opened_at','closed_at',
    'subtotal','service_charge','tax','grand_total','total',
    'paid_cash','paid_card','paid_total','settled_total',
    'customer_display_name','memo'
  ]
  const rows = billsToday.value.map(b => ({
    id: b.id,
    table_no: b.table?.number ?? '',
    opened_at: b.opened_at ?? '',
    closed_at: b.closed_at ?? '',
    subtotal: b.subtotal ?? 0,
    service_charge: b.service_charge ?? 0,
    tax: b.tax ?? 0,
    grand_total: b.grand_total ?? 0,
    total: b.total ?? 0,
    paid_cash: b.paid_cash ?? 0,
    paid_card: b.paid_card ?? 0,
    paid_total: b.paid_total ?? 0,
    settled_total: b.settled_total ?? (b.grand_total || 0),
    customer_display_name: b.customer_display_name ?? '',
    memo: b.memo ?? '',
  }))
  downloadCsv(`bills_${date.value}.csv`, headers, rows)
}

function downloadItemsCsv(){
  const headers = [
    'bill_id','item_id','name','qty','price','subtotal',
    'served_by','category','code'
  ]
  const rows = []
  for (const b of billsToday.value){
    const items = Array.isArray(b.items) ? b.items : []
    for (const it of items){
      rows.push({
        bill_id  : b.id,
        item_id  : it.id,
        name     : it.name ?? '',
        qty      : it.qty ?? 0,
        price    : it.price ?? 0,
        subtotal : it.subtotal ?? 0,
        served_by: it.served_by_cast?.stage_name ?? '',
        category : it.category?.name ?? it.category ?? '',
        code     : it.code ?? '',
      })
    }
  }
  downloadCsv(`bill_items_${date.value}.csv`, headers, rows)
}

/* ----------------- 表示用の派生 ----------------- */
const kpiSalesLabel = computed(() =>
  `${fmtYen(kpi.value.sales_total)}<span>（現金:${fmtYen(kpi.value.sales_cash)} / カード:${fmtYen(kpi.value.sales_card)}）</span>`
)


const kpiOpenLabel = computed(() =>
  `${kpi.value.unsettled_count}/${kpi.value.open_count}`
)
const kpiDutyLabel = computed(() =>
  `${kpi.value.cast_on_duty}/${kpi.value.staff_on_duty}`
)
</script>

<template>
  <div class="owner-dashboard">

    <div class="header d-flex flex-column mb-4">
      <div class="user-info d-flex align-items-center gap-2">
        <Avatar :url="avatarURL" :size="60" class="rounded-circle" />
        <div class="name fs-5 fw-bold">{{ userName }}</div>
      </div>

    </div>

    <div v-if="activeTab === 'home'" class="area">

      <!-- オーナー用：店舗セレクタ -->
      <div v-if="showStoreSelector" class="store-selector">
        <div class="d-flex align-items-center gap-2 mb-1">
          <div class="fw-bold">
            対象店舗
          </div>
          <div class="text-muted small">
            {{ selectedStoreIds.length }}店舗選択中（複数選択可）
          </div>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <button
            v-for="st in availableStores"
            :key="st.id"
            class="btn btn-sm"
            :class="isStoreSelected(st.id) ? 'btn-secondary' : 'btn-outline-secondary'"
            @click="toggleStore(st.id)">
            {{ st.name }}
          </button>
        </div>

      </div>

      <PLPage :store-ids="selectedStoreIds" /><!-- ＊これが出ればいい -->

    </div>

    <div v-if="activeTab === 'bills'" class="area my-4"><!-- Download タブ -->

      <!-- オーナー用：店舗セレクタ（単一選択） -->
      <div v-if="showStoreSelector" class="store-selector">
        <div class="fw-bold mb-2">対象店舗</div>
        <div class="d-flex flex-wrap gap-2">
          <button
            v-for="st in availableStores"
            :key="st.id"
            class="btn btn-sm"
            :class="selectedStoreIds[0] === st.id ? 'btn-secondary' : 'btn-outline-secondary'"
            @click="selectStoreForBills(st.id)">
            {{ st.name }}
          </button>
        </div>
      </div>


      <BillList :store-id="selectedStoreIds[0]" />

    </div>

  </div>


</template>

<style scoped lang="scss">

  .manager-dashboard{
    .card{
      .title{
        font-weight: normal;
        margin: 0;
        padding: 8px;
        text-align: center;
        gap: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .value{
        font-size: 2rem;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
        &.sales{
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          span{
            font-size: 12px;
          }
        }
      }
    }
  }

</style>