<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { api } from '@/api'
import Avatar from '@/components/Avatar.vue'

const router = useRouter()
const bills = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = 30
const searchQuery = ref('')
const dateFilter = ref('today')
const selectedDate = ref(dayjs().format('YYYY-MM-DD'))

const yen = n => `¥${(Number(n || 0)).toLocaleString()}`
const formatDate = s => s ? dayjs(s).format('M/D') : '-'
const formatTime = s => s ? dayjs(s).format('HH:mm') : '-'

// 検索とフィルタリング
const filteredBills = computed(() => {
  let result = bills.value

  // 日付フィルタ
  if (dateFilter.value === 'today' || dateFilter.value === 'date') {
    const targetDate = dateFilter.value === 'today' 
      ? dayjs().format('YYYY-MM-DD')
      : selectedDate.value
    result = result.filter(bill => {
      if (!bill.closed_at) return false
      return dayjs(bill.closed_at).format('YYYY-MM-DD') === targetDate
    })
  }

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
    const { data } = await api.get('billing/bills/', {
      params: {
        closed_at__isnull: false,
        ordering: '-closed_at',
        page_size: 1000 // クライアント側でフィルタリングするため多めに取得
      }
    })
    bills.value = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
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

onMounted(loadBills)
</script>

<template>
  <div class="py-3 py-md-4">

    <!-- フィルタ・検索エリア -->
    <div class="row mb-3 mb-md-4">
      <div class="col-12 col-md-6 mb-3 mb-md-0">
        <!-- 日付セグメント -->
        <div class="d-flex flex-column gap-2">
          <div class="btn-group" role="group">
            <button 
              type="button" 
              class="btn"
              :class="dateFilter === 'today' ? 'btn-primary' : 'btn-outline-primary'"
              @click="dateFilter = 'today'"
            >
              今日
            </button>
            <button 
              type="button" 
              class="btn"
              :class="dateFilter === 'date' ? 'btn-primary' : 'btn-outline-primary'"
              @click="dateFilter = 'date'"
            >
              日付指定
            </button>
            <button 
              type="button" 
              class="btn"
              :class="dateFilter === 'all' ? 'btn-primary' : 'btn-outline-primary'"
              @click="dateFilter = 'all'"
            >
              全期間
            </button>
          </div>
          <input 
            v-if="dateFilter === 'date'"
            v-model="selectedDate"
            type="date" 
            class="form-control"
          />
        </div>
      </div>
      <div class="col-12 col-md-6">
        <!-- 検索ボックス -->
        <input 
          v-model="searchQuery"
          type="text" 
          class="form-control bg-white" 
          placeholder="テーブル名、キャスト名で検索..."
        >
      </div>
    </div>

    <!-- 件数表示 -->
    <div class="text-muted small mb-3">
      {{ filteredBills.length }}件
    </div>
    <div class="color d-flex gap-2 mb-3 align-items-center">
        <div class="badge bg-danger text-white">本指名</div>
        <div class="badge bg-success text-white">場内</div>
        <div class="badge bg-blue text-white">フリー</div>
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
          <div
            class="card bill-card"
            @click="viewDetail(b.id)"
          >
            <div class="card-header">
              <div class="row g-2">
                <div class="col">
                  <div class="label">卓番号</div>
                  <div class="value">{{ b.table?.number ?? '-' }}</div>
                </div>
                <div class="col">
                  <div class="label">開始</div>
                  <div class="value">{{ b.opened_at ? dayjs(b.opened_at).format('HH:mm') : '-' }}</div>
                </div>
                <div class="col">
                  <div class="label">終了</div>
                  <div class="value">{{ b.closed_at ? dayjs(b.closed_at).format('HH:mm') : (b.expected_out ? dayjs(b.expected_out).format('HH:mm') : '-') }}</div>
                </div>
                <div class="col">
                  <div class="label">延長</div>
                  <div class="value">{{ b.ext_minutes ? Math.floor(b.ext_minutes / 30) : '-' }}</div>
                </div>
                <div class="col">
                  <div class="label">人数</div>
                  <div class="value">{{ calcPax(b) || '-' }}</div>
                </div>
                <div class="col">
                  <div class="label">SET数</div>
                  <div class="value">{{ b.set_rounds || '-' }}</div>
                </div>
              </div>
            </div>

            <div class="card-body">
              <!-- キャスト表示 -->
              <div class="casts-section">
                <!-- 今ついているキャスト -->
                <div class="d-flex flex-wrap gap-2 mb-2">
                  <div
                    v-for="p in liveCasts(b).filter(p => p.present)"
                    :key="p.id"
                    class="d-flex align-items-center badge text-light p-2"
                    :class="`bg-${p.color}`"
                  >
                    <Avatar
                      :url="p.avatar"
                      :alt="p.name"
                      :size="16"
                      class="me-1"
                    />
                    <span class="fw-bold">{{ p.name }}</span>
                  </div>
                </div>

                <!-- 過去に付いたキャスト -->
                <div class="d-flex flex-wrap gap-1">
                  <span
                    v-for="p in liveCasts(b).filter(p => !p.present)"
                    :key="p.id"
                    class="badge bg-secondary-subtle text-dark small"
                  >
                    {{ p.name }}
                  </span>
                </div>
              </div>
            </div>

            <div class="card-footer">
              <div class="row g-2">
                <div class="col-6">
                  <div class="label">小計</div>
                  <div class="value">¥{{ b.subtotal?.toLocaleString() || '-' }}</div>
                </div>
                <div class="col-6">
                  <div class="label">合計</div>
                  <div class="value">¥{{ (b.settled_total ?? (b.closed_at ? b.total : b.grand_total))?.toLocaleString() || '-' }}</div>
                </div>
                <div class="col-12">
                  <div class="label">メモ</div>
                  <div v-if="hasMemo(b)" class="memo-content">{{ b.memo }}</div>
                  <div v-else class="text-muted small">メモなし</div>
                </div>
              </div>
            </div>
          </div>
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

.bill-card {
  position: relative;
  cursor: pointer;
  border: 1px solid #ddd;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  &.closed::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.3);
    pointer-events: none;
    border-radius: inherit;
  }
}

.card-header {
  background-color: white;
  .col {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
  }
}

.card-footer {
  border-top: 1px solid #e9ecef;
  background-color: white;
}

.label {
  font-size: 0.75rem;
  color: #666;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}

.value {
  font-size: 1.25rem;
  font-weight: bold;
  color: #333;
}

.memo-content {
  white-space: pre-wrap;
  word-break: break-word;
  padding: 0.5rem;
  background-color: #f9f9f9;
  border-radius: 4px;
  font-size: 0.875rem;
}
</style>
