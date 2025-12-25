<!-- src/views/ManagerDashboard.vue -->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import dayjs from 'dayjs'
import {
  getBillDailyPL,
  fetchBills,
  fetchCastShifts,
  fetchStaffShifts,
} from '@/api'
import MiniTip from '@/components/MiniTip.vue'
import Avatar from '@/components/Avatar.vue'
import CsvPreviewTable from '@/components/CsvPreviewTable.vue'
import { useUser } from '@/stores/useUser'
import { useProfile } from '@/composables/useProfile'
import PersonnelExpensesSection from '@/components/expenses/PersonnelExpensesSection.vue'

const user = useUser()
const { avatarURL } = useProfile()

const userName = computed(() => {
  return user.me?.username || user.me?.email || 'ユーザー'
})

const showOpenTip = ref(false)
const showDutyTip = ref(false)

/* ----------------- タブ管理 ----------------- */
const activeTab = ref('sales') // 'sales', 'bills', 'download'
const csvTab = ref('bills') // 'bills', 'payroll'

function switchTab(tabId) {
  activeTab.value = tabId
}

function switchCsvTab(tabId) {
  csvTab.value = tabId
}

/* ----------------- 日付（単日） ----------------- */
const date = ref(dayjs().format('YYYY-MM-DD'))

/* 経費タブ用日付範囲 */
const expenseFrom = ref(dayjs().format('YYYY-MM-DD'))
const expenseTo = ref(dayjs().format('YYYY-MM-DD'))

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

// 給与CSV用
const payrollCsvText = ref('')
const payrollPreviewHeaders = ref([])
const payrollPreviewRows = ref([])



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
    const pl = await getBillDailyPL(d, { cache: false })

    // 2) 伝票（クライアントで当日抽出）- キャッシュ無効化
    const allBills = await fetchBills({ ordering: '-opened_at' }, { cache: false }).catch(()=>[])
    const onlyToday = (Array.isArray(allBills?.results) ? allBills.results : allBills || [])
      .filter(b => b.opened_at && dayjs(b.opened_at).isSame(d, 'day'))
    console.log('[Dashboard] allBills count:', Array.isArray(allBills?.results) ? allBills.results.length : allBills.length)
    console.log('[Dashboard] onlyToday count:', onlyToday.length)
    console.log('[Dashboard] onlyToday:', onlyToday)

    // まず今日の伝票（削除除外込み）を確定
    const isDeletedBill = (b) => {
      // 論理削除フィールドで判定
      return Boolean(b?.is_deleted || b?.deleted_at || b?.status === 'deleted' || b?.is_active === false)
    }

    // 重複除去関数
    const uniqById = (arr) => Array.from(new Map(arr.map(b => [String(b.id), b])).values())

    const todayBills = uniqById(onlyToday.filter(b => !isDeletedBill(b)))
    billsToday.value = todayBills

    // 重複チェック + 削除っぽいフラグの実態確認 + pax確認
    const rows = todayBills.map(b => ({
      id: b.id,
      opened_at: b.opened_at,
      closed_at: b.closed_at,
      pax: b.pax,
      // 削除判定に使えそうな候補を全部見える化（実際に何が返ってきてるか確認する）
      is_deleted: b.is_deleted,
      deleted_at: b.deleted_at,
      is_active: b.is_active,
      status: b.status,
    }))
    console.table(rows)

    const ids = todayBills.map(b => b.id)
    const dupIds = ids.filter((id, i) => ids.indexOf(id) !== i)
    console.log('[todayBills] count=', todayBills.length, 'unique=', new Set(ids).size, 'dupIds=', dupIds)

    // 来店数 = PAX合計（未入力は 0）
    const paxTotal = todayBills.reduce((s, b) => s + Number(b?.pax || 0), 0)
    console.log('[paxTotal]', paxTotal)

    // オープン中
    const openCnt = todayBills.filter(b => !b.closed_at).length

    // 決済済み（= closed かつ 支払い>=会計）
    const isPaid = (b) => {
      const st = Number((b.settled_total ?? b.grand_total) || 0)
      const pt = Number(b.paid_total || 0)
      return Boolean(b.closed_at) && pt >= st && st > 0
    }
    const paidCnt = todayBills.filter(isPaid).length
    console.log('[Dashboard] openCnt:', openCnt, 'paidCnt:', paidCnt)

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
  visitors    : paxTotal,
  open_count  : openCnt,
  unsettled_count: paidCnt,  // 名前は unsettled_count だが実際には "決済済み" の数
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

onMounted(loadAll)
watch(date, loadAll)

/* ----------------- CSV（フロント生成） ----------------- */
const billsCsvHeaders = [
  'id','table_no','opened_at','closed_at',
  'subtotal','service_charge','tax','grand_total','total',
  'paid_cash','paid_card','paid_total','settled_total',
  'customer_display_name','memo'
]

const billsCsvRows = computed(() => {
  return billsToday.value.map(b => ({
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
})

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
  downloadCsv(`bills_${date.value}.csv`, billsCsvHeaders, billsCsvRows.value)
}

function parseCsvForPreview(text) {
  // BOM除去
  let csv = text
  if (csv.charCodeAt(0) === 0xFEFF) {
    csv = csv.slice(1)
  }

  const lines = csv.split(/\r?\n/).filter(line => line.trim())
  if (!lines.length) {
    payrollPreviewHeaders.value = []
    payrollPreviewRows.value = []
    return
  }

  // 簡易CSV行パース（ダブルクォート対応）
  function parseCsvLine(line) {
    const result = []
    let current = ''
    let inQuotes = false
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i]
      const next = line[i + 1]
      
      if (char === '"') {
        if (inQuotes && next === '"') {
          current += '"'
          i++
        } else {
          inQuotes = !inQuotes
        }
      } else if (char === ',' && !inQuotes) {
        result.push(current)
        current = ''
      } else {
        current += char
      }
    }
    result.push(current)
    return result
  }

  // ヘッダ
  const headers = parseCsvLine(lines[0])
  payrollPreviewHeaders.value = headers

  // データ行（先頭50行まで）
  const rows = []
  const maxRows = Math.min(lines.length - 1, 50)
  for (let i = 1; i <= maxRows; i++) {
    const values = parseCsvLine(lines[i])
    const row = {}
    headers.forEach((h, idx) => {
      row[h] = values[idx] ?? ''
    })
    rows.push(row)
  }
  payrollPreviewRows.value = rows
}

async function downloadPayrollCsv() {
  try {
    loading.value = true
    const storeId = user.storeId
    
    const res = await fetch('/api/billing/payroll/runs/export.csv', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Store-Id': String(storeId),
        'Authorization': `Token ${user.token}`,
      },
      body: JSON.stringify({
        from: date.value,
        to: date.value,
        note: '',
      }),
    })

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }

    const blob = await res.blob()
    const text = await blob.text()
    
    // プレビュー更新
    payrollCsvText.value = text
    parseCsvForPreview(text)

    // ダウンロード
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `payroll_${date.value}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    errorMsg.value = '給与CSVダウンロードに失敗しました'
  } finally {
    loading.value = false
  }
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
  `${kpi.value.unsettled_count}/${kpi.value.open_count}`  // 当日のオープン中（決済待ち）伝票数
)
const kpiDutyLabel = computed(() =>
  `${kpi.value.cast_on_duty}/${kpi.value.staff_on_duty}`
)
</script>

<template>
  <div class="manager-dashboard">

    <div class="header d-flex justify-content-between align-items-center mb-4">
      <div class="user-info d-flex align-items-center gap-2">
        <Avatar :url="avatarURL" :size="60" class="rounded-circle" />
        <div class="name fs-5 fw-bold">{{ userName }}</div>
      </div>
      <div class="df-center gap-3 fs-4">

        <RouterLink :to="{ name:'mng-bills' }">
          <IconReceiptYen />
        </RouterLink>
        <RouterLink :to="{ name:'mng-pl' }">
          <IconChartHistogram />
        </RouterLink>
      </div>
    </div>


    <nav class="row border-bottom g-1 mb-4">
      <div
        class="col-3"
        :class="{ 'border-bottom border-3 border-secondary': activeTab === 'sales' }">
        <button 
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('sales')">
          売上
        </button>
      </div>
      <div
        class="col-3"
        :class="{ 'border-bottom border-3 border-secondary': activeTab === 'bills' }">
        <button 
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('bills')">
          伝票
        </button>
      </div>
      <div
        class="col-3"
        :class="{ 'border-bottom border-3 border-secondary': activeTab === 'expenses' }">
        <button 
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('expenses')">
          経費
        </button>
      </div>
      <div
        class="col-3"
        :class="{ 'border-bottom border-3 border-secondary': activeTab === 'download' }">
        <button
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="switchTab('download')">
          CSV
        </button>
      </div>
    </nav>

    <!-- ロード／エラー -->
    <div v-if="loading">読み込み中…</div>
    <div v-else-if="errorMsg">{{ errorMsg }}</div>

    <!-- KPIカード -->
    <div v-show="activeTab === 'sales'" v-else>
      <div class="area card-area row g-3">
        <!-- 置き換え：今日の売上カード内 -->
        <div class="col-12 col-md-3 d-flex">
          <div class="card h-100 w-100">
            <div class="card-header title">今日の売上</div>
            <div class="card-body value sales">
              <!-- 合計 -->
              <div class="my-3">{{ fmtYen(kpi.sales_total) }}</div>

              <!-- 現金/カード（2段・バッジ付き） -->
              <div class="box fs-5 d-flex flex-column align-items-center gap-2">
                <div class="wrap d-flex align-items-center gap-2">
                  <span class="badge bg-secondary">現金</span>
                  <span class="fw-normal">{{ fmtYen(kpi.sales_cash) }}</span>
                </div>
                <div class="wrap d-flex align-items-center gap-2">
                  <span class="badge bg-secondary">カード</span>
                  <span class="fw-normal">{{ fmtYen(kpi.sales_card) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- 来客数 -->
        <div class="col-4 col-md-3 d-flex">
          <div class="card h-100 w-100">
            <div class="card-header title">来客数</div>
            <div class="card-body value">{{ kpi.visitors }}</div>
          </div>
        </div>

        <!-- オープン中 -->
        <div class="col-4 col-md-3 d-flex">
          <div class="card h-100 w-100">
            <div class="card-header title">伝票
              <MiniTip v-model="showOpenTip" text="決済済み/オープン中" align="right">
                <button type="button" class="btn btn-link p-0 text-muted d-flex align-items-center" @click.stop="showOpenTip = !showOpenTip">
                  <IconInfoCircle />
                </button>
              </MiniTip>
            </div>
            <div class="card-body value">{{ kpiOpenLabel }}</div>
          </div>
        </div>

        <!-- 出勤数 -->
        <div class="col-4 col-md-3 d-flex">
          <div class="card h-100 w-100">
            <div class="card-header title">出勤数
              <MiniTip v-model="showDutyTip" text="キャスト/スタッフ" align="right">
                <button type="button" class="btn btn-link p-0 text-muted d-flex align-items-center" @click.stop="showDutyTip = !showDutyTip">
                  <IconInfoCircle />
                </button>
              </MiniTip>
            </div>
            <div class="card-body value">{{ kpiDutyLabel }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 伝票一覧（ミニ） -->
    <div v-show="activeTab === 'bills'" class="area my-4">
      <div class="h4 fw-bold text-center">今日の伝票</div>
      <div class="text-center my-5" v-if="!billsToday.length">まだありません</div>
      <div v-else>
        <div v-for="b in billsToday" :key="b.id" class="mb-3">
          <div class="card p-3">
            <div class="wrap d-flex align-items-center gap-2">
              <div>#{{ b.id }}</div>
              <div><IconPinned class="me-1"/>{{ b.table?.number ?? '-' }}</div>
              <div v-if="b.customer_display_name">
                <IconUserScan />{{ b.customer_display_name }}
              </div>
            </div>
            <div class="wrap my-2">
              <div class="fs-5 mb-1">
                <IconClock />{{ fmtTime(b.opened_at) }}-{{ fmtTime(b.closed_at || b.expected_out) }}
              </div>
              <div class="d-flex align-items-center gap-2">
                <span class="badge bg-secondary">合計</span>
                <span class="fs-4 fw-bold">{{ fmtYen(b.settled_total ?? (b.closed_at ? b.total : b.grand_total)) }}</span>
              </div>

            </div>
            <div v-if="b.memo">
              メモ: {{ b.memo }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-show="activeTab === 'expenses'" class="area my-4">

        <div class="row g-2 align-items-center mb-3">
          <div class="col-auto">
            <label class="form-label small mb-0">開始日</label>
            <input type="date" class="form-control form-control-sm bg-white" v-model="expenseFrom" />
          </div>
          <div class="col-auto">
            <label class="form-label small mb-0">終了日</label>
            <input type="date" class="form-control form-control-sm bg-white" v-model="expenseTo" />
          </div>
        </div>

      <PersonnelExpensesSection 
        :range-from="expenseFrom"
        :range-to="expenseTo"
      />
    </div>

    <!-- CSV -->
    <div v-show="activeTab === 'download'" class="area my-4">
      <div class="h4 fw-bold text-center">CSVダウンロード</div>

      <nav class="row border-bottom g-1 mb-3">
        <div
          class="col-6"
          :class="{ 'border-bottom border-3 border-secondary': csvTab === 'bills' }">
          <button 
            class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
            @click="switchCsvTab('bills')">
            伝票
          </button>
        </div>
        <div
          class="col-6"
          :class="{ 'border-bottom border-3 border-secondary': csvTab === 'payroll' }">
          <button 
            class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
            @click="switchCsvTab('payroll')">
            給与
          </button>
        </div>
      </nav>

      <div v-show="csvTab === 'bills'" class="card mb-3">
        <div class="card-header">本日の伝票CSVプレビュー</div>
        <div class="card-body">
          <CsvPreviewTable 
            :headers="billsCsvHeaders" 
            :rows="billsCsvRows" 
            :maxRows="20" 
          />
        </div>
        <div class="card-footer">
          <button class="btn btn-sm btn-success w-100" type="button" @click="downloadBillsCsv">
            伝票CSVダウンロード
          </button>
        </div>
      </div>

      <div v-show="csvTab === 'payroll'" class="card">
        <div class="card-header">本日の給与CSVプレビュー</div>
        <div class="card-body">
          <CsvPreviewTable 
            :headers="payrollPreviewHeaders" 
            :rows="payrollPreviewRows" 
            :maxRows="20" 
          />
        </div>
        <div class="card-footer">
          <button class="btn btn-sm btn-success w-100" type="button" @click="downloadPayrollCsv">
            給与CSVダウンロード
          </button>
        </div>
      </div>

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