<script setup>
import { ref, computed, onMounted, watch, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { api } from '@/api'
import Avatar from '@/components/Avatar.vue'
import BillListCard from '@/components/BillListCard.vue'
import { deleteBill } from '@/api'

const props = defineProps({
  storeId: { type: Number, default: null }
})

const router = useRouter()
const bills = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = 30
const searchQuery = ref('')
const dateFilter = ref('today')
const selectedDate = ref(dayjs().format('YYYY-MM-DD'))
const isSelectionMode = ref(false)
const selectedIds = ref(new Set())
const showDateInput = ref(false)

const yen = n => `¥${(Number(n || 0)).toLocaleString()}`
const formatDate = s => s ? dayjs(s).format('M/D') : '-'
const formatTime = s => s ? dayjs(s).format('HH:mm') : '-'

// 検索とフィルタリング
const filteredBills = computed(() => {
  let result = bills.value

  // 日付フィルタ
  if (dateFilter.value === 'today') {
    const targetDate = dayjs().format('YYYY-MM-DD')
    result = result.filter(bill => {
      if (!bill.closed_at) return false
      return dayjs(bill.closed_at).format('YYYY-MM-DD') === targetDate
    })
  } else if (dateFilter.value === 'date') {
    result = result.filter(bill => {
      if (!bill.closed_at) return false
      return dayjs(bill.closed_at).format('YYYY-MM-DD') === selectedDate.value
    })
  }
  // dateFilter.value === 'all' の場合はフィルタなし

  // 検索クエリ
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(bill => {
      const tableName = (bill.table?.code || bill.table?.number || '').toString().toLowerCase()
      const castNames = (bill.stays || [])
        .map(s => (s.cast?.stage_name || s.cast?.name || '').toLowerCase())
        .join(' ')
      return tableName.includes(query) || castNames.includes(query)
    })
  }

  return result
})

// ページネーション
const totalPages = computed(() => Math.ceil(filteredBills.value.length / pageSize))

const paginatedBills = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredBills.value.slice(start, end)
})

const displayPages = computed(() => {
  const pages = []
  const maxDisplay = 5
  let start = Math.max(1, currentPage.value - Math.floor(maxDisplay / 2))
  let end = Math.min(totalPages.value, start + maxDisplay - 1)
  
  if (end - start + 1 < maxDisplay) {
    start = Math.max(1, end - maxDisplay + 1)
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

// フィルタ変更時はページをリセット
watch([searchQuery, dateFilter, selectedDate], () => {
  currentPage.value = 1
})

async function loadBills() {
  loading.value = true
  try {
    const config = {
      params: {
        closed_at__isnull: false,
        ordering: '-closed_at',
        page_size: 1000, // クライアント側でフィルタリングするため多めに取得
        _ts: Date.now(), // キャッシュバスター
      },
      cache: false, // Service Worker/HTTPキャッシュ回避
    }
    // 店舗ID指定がある場合はヘッダで明示
    if (props.storeId) {
      config.headers = {
        'X-Store-Id': String(props.storeId),
        'X-Store-ID': String(props.storeId)
      }
    }
    const { data } = await api.get('billing/bills/', config)
    bills.value = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
    // デバッグ：最初のbillをログに出力
    if (bills.value.length > 0) {
      console.log('First bill data:', bills.value[0])
      console.log('set_rounds:', bills.value[0].set_rounds)
      console.log('ext_minutes:', bills.value[0].ext_minutes)
      console.log('items:', bills.value[0].items)
    }
  } catch (e) {
    console.error(e)
    alert('伝票の取得に失敗しました')
  } finally {
    loading.value = false
  }
}

function viewDetail(billId) {
  router.push({ name: 'BillDetail', params: { id: billId } })
}

function getCastBadgeClass(stay) {
  // 本指名（stay_type 'nom'）
  if (stay.is_honshimei || stay.stay_type === 'nom') return 'bg-danger'
  // 場内指名（stay_type 'in'）
  if (stay.stay_type === 'in') return 'bg-success'
  // 同伴（stay_type 'dohan'）
  if (stay.is_dohan || stay.stay_type === 'dohan') return 'bg-secondary'
  // ヘルプ（free で is_help=true）
  if (stay.is_help) return 'bg-purple'
  // フリーその他
  return 'bg-blue'
}

// DashboardList と同じユーティリティ関数
function isSameDay(d1, d2) {
  if (!d1 || !d2) return false
  return dayjs(d1).isSame(d2, 'day')
}

function calcPax(b) {
  if (!b) return 0
  const items = b.items || []
  let male = 0, female = 0
  for (const it of items) {
    const code = it.master?.code || it.code || ''
    if (code.includes('Male')) male += (it.qty || 0)
    else if (code.includes('Female')) female += (it.qty || 0)
  }
  const total = male + female
  return total > 0 ? total : (b.pax || 0)
}

function liveCasts(b) {
  const map = new Map();

  (b.stays || []).forEach(s => {
    const id = s.cast?.id
    if (!id) return

    const present = !s.left_at
    const entered = new Date(s.entered_at).getTime()

    const prev = map.get(id)
    if (
      !prev ||
      (present && !prev.present) ||
      entered > prev.entered
    ) {
      map.set(id, { stay: s, present, entered })
    }
  })

  return [...map.values()].map(({ stay, present }) => ({
    id: stay.cast?.id,
    name: stay.cast?.stage_name || "N/A",
    avatar: stay.cast?.avatar_url || "/img/user-default.png",
    color: stay.stay_type === "nom" ? "danger"
         : stay.stay_type === "in" ? "success"
         : stay.stay_type === "dohan" ? "secondary"
         : "blue",
    present
  }))
}

function hasMemo(b) {
  return !!(b?.memo && String(b.memo).trim())
}

function toggleSelectMode() {
  isSelectionMode.value = !isSelectionMode.value
  if (!isSelectionMode.value) {
    selectedIds.value.clear()
  }
}

function handleSelect(billId) {
  if (selectedIds.value.has(billId)) {
    selectedIds.value.delete(billId)
  } else {
    selectedIds.value.add(billId)
  }
}

function handleEdit(billId) {
  router.push({ name: 'BillDetail', params: { id: billId } })
}

async function bulkDelete() {
  if (!selectedIds.value.size) return
  if (!window.confirm(`${selectedIds.value.size} 件を削除しますか？`)) return

  try {
    const ids = [...selectedIds.value]
    await Promise.all(ids.map(id => deleteBill(id)))
    selectedIds.value.clear()
    isSelectionMode.value = false
    await loadBills()
  } catch (e) {
    console.error(e)
    alert('削除に失敗しました')
  }
}

function applyDateFilter() {
  dateFilter.value = 'date'
  showDateInput.value = false
}

function applyAllPeriods() {
  dateFilter.value = 'all'
  showDateInput.value = false
}

onMounted(loadBills)
// タブ戻りや keep-alive 復帰時にも最新取得
onActivated(loadBills)
watch(() => props.storeId, loadBills)
</script>

<template>
  <div class="py-3 py-md-4">

    <!-- フィルタ・検索エリア -->
    <div class="row g-2">
      <div class="col-12">
        <!-- 検索ボックス -->
        <input 
          v-model="searchQuery"
          type="text" 
          class="form-control bg-white" 
          placeholder="テーブル名、キャスト名で検索..."
        >
      </div>
      <div class="col-6">
      <!-- 日付入力 -->
        <input 
          v-show="dateFilter === 'date'"
          v-model="selectedDate"
          type="date" 
          class="form-control bg-white"
        />
      </div>
      <div class="col-3">
        <button
          class="btn btn-sm btn-secondary w-100 h-100"
          @click="applyDateFilter"
        >
          検索
        </button>
      </div>
      <div class="col-3">
        <button
          class="btn btn-sm btn-secondary w-100 h-100"
          @click="applyAllPeriods"
        >
          全期間
        </button>
      </div>
    </div>

    <!-- 件数表示 -->
    <div class="d-flex align-items-center justify-content-between my-3">
      <div class="color d-flex gap-2 align-items-center">
          <div class="badge bg-danger text-white">本指名</div>
          <div class="badge bg-success text-white">場内</div>
          <div class="badge bg-blue text-white">フリー</div>
      </div>
      <div class="text-muted small">
        検索結果 : {{ filteredBills.length }}件
      </div>
    </div>
    <div class="wrap d-flex align-items-center justify-content-end gap-2">
      <button
        class="btn btn-sm d-flex align-items-center gap-1"
        :class="isSelectionMode ? 'btn-danger' : 'btn-secondary'"
        @click="toggleSelectMode"
      >
        <IconTrash />{{ isSelectionMode ? 'キャンセル' : '削除' }}
      </button>
      <button
        v-if="isSelectionMode && selectedIds.size > 0"
        class="btn btn-sm btn-danger d-flex align-items-center gap-1"
        @click="bulkDelete"
      >
        <IconTrash />{{ selectedIds.size }}件削除
      </button>
    </div>


    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">読み込み中...</span>
      </div>
    </div>

    <div v-else-if="filteredBills.length === 0"
      class="df-center fw-bold fs-5"
      style="height: 50vh;">
      {{ bills.length === 0 ? '確定済みの伝票はありません' : '検索条件に一致する伝票はありません' }}
    </div>

    <div v-else>
      <!-- カードビュー -->
      <div class="cards-container">
        <template v-for="(b, idx) in paginatedBills" :key="b.id">
          <!-- 見出し行：前の伝票と日付が違えば出力 -->
          <div
            v-if="idx === 0 || !isSameDay(paginatedBills[idx-1].closed_at, b.closed_at)"
            class="date-header"
          >
            {{ b.closed_at ? dayjs(b.closed_at).format('YYYY/MM/DD(ddd)') : '日付未定' }}
          </div>

          <!-- カード -->
          <BillListCard
            :bill="b"
            :isSelectable="isSelectionMode"
            :isSelected="selectedIds.has(b.id)"
            @select="handleSelect"
            @edit="handleEdit"
          />
        </template>
      </div>

      <!-- ページネーション -->
      <nav v-if="totalPages > 1" aria-label="Page navigation" class="mt-4">
        <ul class="pagination justify-content-center flex-wrap">
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <a class="page-link" href="#" @click.prevent="currentPage > 1 && (currentPage--)">前へ</a>
          </li>
          <li 
            v-for="page in displayPages" 
            :key="page"
            class="page-item" 
            :class="{ active: page === currentPage }"
          >
            <a class="page-link" href="#" @click.prevent="currentPage = page">{{ page }}</a>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <a class="page-link" href="#" @click.prevent="currentPage < totalPages && (currentPage++)">次へ</a>
          </li>
        </ul>
      </nav>
    </div>
  </div>
</template>

<style scoped lang="scss">
.cards-container {
  display: grid;
  gap: 1rem;
  margin-bottom: 4rem;
}

.date-header {
  font-weight: bold;
  font-size: 1rem;
  padding: 1rem 0 0.5rem 0;
  color: #666;
  border-bottom: 1px solid #ccc;
}
</style>
