<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { api } from '@/api'

const router = useRouter()
const bills = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = 30
const searchQuery = ref('')
const dateFilter = ref('today')

const yen = n => `¥${(Number(n || 0)).toLocaleString()}`
const formatDate = s => s ? dayjs(s).format('M/D') : '-'
const formatTime = s => s ? dayjs(s).format('HH:mm') : '-'

// 検索とフィルタリング
const filteredBills = computed(() => {
  let result = bills.value

  // 日付フィルタ
  if (dateFilter.value === 'today') {
    const today = dayjs().format('YYYY-MM-DD')
    result = result.filter(bill => {
      if (!bill.closed_at) return false
      return dayjs(bill.closed_at).format('YYYY-MM-DD') === today
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
watch([searchQuery, dateFilter], () => {
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

onMounted(loadBills)
</script>

<template>
  <div class="py-3 py-md-4">

    <!-- フィルタ・検索エリア -->
    <div class="row mb-3 mb-md-4">
      <div class="col-12 col-md-6 mb-3 mb-md-0">
        <!-- 日付セグメント -->
        <div class="btn-group w-100" role="group">
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
            :class="dateFilter === 'all' ? 'btn-primary' : 'btn-outline-primary'"
            @click="dateFilter = 'all'"
          >
            全期間
          </button>
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
        <div class="badge bg-blue">フリー</div>
        <div class="badge bg-success">場内</div>
        <div class="badge bg-danger">本指名</div>
        <div class="badge bg-purple">ヘルプ</div>
        <div class="badge bg-secondary">同伴</div>
    </div>
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">読み込み中...</span>
      </div>
    </div>

    <div v-else-if="filteredBills.length === 0" class="alert alert-info">
      {{ bills.length === 0 ? '確定済みの伝票はありません' : '検索条件に一致する伝票はありません' }}
    </div>

    <div v-else>
      <!-- カードビュー -->
      <div class="row g-2 g-md-3">
        <div 
          v-for="bill in paginatedBills" 
          :key="bill.id"
          class="col-12 col-md-6 col-lg-4 col-xl-3"
        >
          <div 
            class="card bill-card h-100 p-3"
            @click="viewDetail(bill.id)"
          >

              <div class="card-title fs-5 d-flex flex-column gap-2 mb-0">
                <div class="d-flex align-items-center gap-3">
                  <span class="fw-bold">#{{ bill.id }}</span>
                    <div class="wrap df-center gap-1">
                        <IconPinned />{{ bill.table?.code || bill.table?.number || 'テーブル未設定' }}
                    </div>
                    <div class="df-center gap-1">
                        <IconClock />
                        <div class="wrap">
                        {{ formatDate(bill.opened_at) }} {{ formatTime(bill.opened_at) }}
                        -{{ formatTime(bill.closed_at) }}
                        </div>
                    </div>
                </div>
                <div v-if="bill.stays && bill.stays.length > 0" class="col-12">
                    <div class="d-flex flex-wrap gap-1">
                    <span 
                        v-for="(stay, idx) in bill.stays.slice(0, 5)" 
                        :key="idx"
                        class="badge"
                        :class="getCastBadgeClass(stay)"
                    >
                        {{ stay.cast?.stage_name || stay.cast?.name || '未設定' }}
                    </span>
                    <span v-if="bill.stays.length > 5" class="badge bg-secondary">
                        +{{ bill.stays.length - 5 }}
                    </span>
                    </div>
                </div>
              </div>

              <div class="card-body row p-0 mt-2">
                <div class="col-6 d-flex align-items-center gap-2">
                  <div class="">小計</div>
                  <div class="fw-bold fs-3">{{ yen(bill.subtotal) }}</div>
                </div>
                <div class="col-6 d-flex align-items-center gap-2">
                  <div class="">合計</div>
                  <div class="fw-bold fs-3">{{ yen(bill.grand_total || bill.total) }}</div>
                </div>
              </div>

          </div>
        </div>
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

<style scoped>
</style>
