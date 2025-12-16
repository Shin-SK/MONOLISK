<!-- StaffMypage.vue -->
<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import RankingBlock from '@/components/RankingBlock.vue'
import CustomerDetailModal from '@/components/CustomerDetailModal.vue'
import Avatar from '@/components/Avatar.vue'
import dayjs from 'dayjs'
import {
  fetchBills,
  createCastShift,
  fetchCastShiftHistory,
  fetchCastRankings,
  fetchStoreNotices
} from '@/api'
import { useUser } from '@/stores/useUser'
import { useProfile } from '@/composables/useProfile'
import { yen } from '@/utils/money'

/* ---------- 現在のログインユーザーの情報取得 ---------- */
const userStore = useUser()
const { displayName, avatarURL } = useProfile()

// ユーザー名表示
const userName = computed(() => displayName.value || userStore.me?.username || 'ユーザー')

/* ---------- 日付 ---------- */
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))

/* ---------- 状態 ---------- */
const shifts      = ref([])
const rankings    = ref([])
const notices     = ref([])
const draftShifts = ref([])
const allCustomerBills = ref([])

/* ---------- シフト月フィルタ ---------- */
const selectedMonth = ref(dayjs().format('YYYY-MM'))

/* ---------- タブ ---------- */
const activeTab = ref('home')

// 顧客情報一覧の絞り込み
const customerSearch = ref('')
const customerMinVisit = ref(0)
const customerSort = ref('latest') // latest / visits

/* ---------- util ---------- */
const fmt = d => d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '–'

/* ---------- データ取得 ---------- */
async function loadShifts () {
  shifts.value = await fetchCastShiftHistory(userStore.me?.id, {
    from: dateFrom.value,
    to  : dateTo.value,
  })
}
async function loadRankings () {
  rankings.value = await fetchCastRankings({
    from: dateFrom.value,
    to  : dateTo.value,
  })
}
async function loadNotices () {
  const data = await fetchStoreNotices({ status:'published', ordering:'-pinned,-publish_at,-created_at', limit:20 })
  notices.value = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
}
async function loadAllCustomerBills () {
  allCustomerBills.value = (await fetchBills({}))
    .filter(b => (b.customer_display_name ?? '').trim().length)
}
async function loadAll () {
  await Promise.all([ loadShifts(), loadRankings(), loadNotices(), loadAllCustomerBills() ])
}

/* ---------- 計算 ---------- */
// ランキング配列ガード
const monthlyRows = computed(() => Array.isArray(rankings.value) ? rankings.value : [])

// フィルタされたシフト
const filteredShifts = computed(() => {
  if (!selectedMonth.value) return shifts.value
  return shifts.value.filter(s => {
    if (!s.plan_start) return false
    return dayjs(s.plan_start).format('YYYY-MM') === selectedMonth.value
  })
})

// 全顧客の最新来店情報
const allCustomersList = computed(() => {
  const grouped = {}
  for (const b of allCustomerBills.value) {
    const name = b.customer_display_name || '(名前なし)'
    if (!grouped[name]) {
      grouped[name] = []
    }
    grouped[name].push(b)
  }
  
  return Object.entries(grouped).map(([name, bills]) => {
    const sorted = bills.sort((a, b) => 
      dayjs(b.opened_at).valueOf() - dayjs(a.opened_at).valueOf()
    )
    const latest = sorted[0]
    
    return {
      name,
      visitCount: bills.length,
      latestVisit: latest.opened_at,
      latestBillId: latest.id,
      latestSubtotal: latest.subtotal,
      casts: latest.stays?.map(s => s.cast?.stage_name || s.cast?.name).filter(Boolean) || []
    }
  }).sort((a, b) => dayjs(b.latestVisit).valueOf() - dayjs(a.latestVisit).valueOf())
})

// 全顧客の最新来店情報（フィルタ付き）
const filteredAllCustomersList = computed(() => {
  const q = (customerSearch.value || '').trim().toLowerCase()
  const minV = Number(customerMinVisit.value || 0)

  let list = Array.isArray(allCustomersList.value) ? allCustomersList.value : []

  if (q) {
    list = list.filter(c => (c.name || '').toLowerCase().includes(q))
  }
  if (minV > 0) {
    list = list.filter(c => (c.visitCount || 0) >= minV)
  }

  if (customerSort.value === 'visits') {
    list = list.slice().sort((a,b) => (b.visitCount||0) - (a.visitCount||0))
  } else {
    list = list.slice().sort((a,b) => dayjs(b.latestVisit).valueOf() - dayjs(a.latestVisit).valueOf())
  }
  return list
})

/* ---------- タブ切り替え ---------- */
function switchTab(k) {
  activeTab.value = k
}

/* ---------- シフト申請 ---------- */
const form = reactive({ start:'', end:'' })

function addDraft () {
  const s = String(form.start || '').trim()
  const e = String(form.end   || '').trim()
  if (!s || !e) { alert('開始と終了を入力してください'); return }
  const start = dayjs(s)
  const end   = dayjs(e)
  if (!start.isValid() || !end.isValid()) { alert('日時の形式が不正です'); return }
  if (end.isSameOrBefore(start)) { alert('終了は開始より後にしてください'); return }

  draftShifts.value.push({
    plan_start: start.toDate(),
    plan_end  : end.toDate(),
  })

  form.start = ''
  form.end   = ''
}

function removeDraft(i){
  draftShifts.value.splice(i, 1)
}

const submitting = ref(false)
async function submitAll () {
  if (!draftShifts.value.length) return
  const userId = userStore.me?.id
  if (!userId) { alert('ユーザー情報が未取得です'); return }
  submitting.value = true
  try {
    for (const d of draftShifts.value) {
      await createCastShift({
        user_id   : userId,
        plan_start: dayjs(d.plan_start).toISOString(),
        plan_end  : dayjs(d.plan_end).toISOString(),
      })
    }
    draftShifts.value = []
    await loadShifts()
    alert('申請を送信しました')
  } catch (e) {
    console.error('submitAll failed', e)
    alert('申請に失敗しました')
  } finally {
    submitting.value = false
  }
}

/* ---------- 顧客モーダル ---------- */
const showCustomerModal = ref(false)
const selectedBillId    = ref(null)
const selectedCustomerStats = ref(null)

function openCustomer(id) {
  selectedBillId.value = id
  try {
    const billObj = allCustomerBills.value.find(b => b.id === id)
    if (billObj) {
      const name = billObj.customer_display_name || ''
      const sameCustomerBills = allCustomerBills.value.filter(b => (b.customer_display_name || '') === name)
      const visitCount = sameCustomerBills.length
      const latestVisit = sameCustomerBills.length
        ? sameCustomerBills
            .map(b => b.opened_at)
            .sort((a,b) => dayjs(b).valueOf() - dayjs(a).valueOf())[0]
        : null
      selectedCustomerStats.value = { name, visit_count: visitCount, last_visit_at: latestVisit }
    } else {
      selectedCustomerStats.value = null
    }
  } catch { selectedCustomerStats.value = null }
  showCustomerModal.value = true
}

function closeCustomerModal(){
  showCustomerModal.value = false
}


/* ---------- 監視 ---------- */
watch([dateFrom, dateTo], () => { loadShifts(); loadRankings() })

/* ---------- 起動 ---------- */
onMounted(async () => {
  await loadAll()
})

</script>

<template>

  <div class="header d-flex justify-content-between align-items-center mb-3">
    <div class="user-info d-flex align-items-center gap-2">
      <Avatar :url="avatarURL" :size="60" class="rounded-circle" />
      <div class="name fs-5 fw-bold">{{ userName }}</div>
    </div>
  </div>

  <nav class="row border-bottom g-1 mb-4">
    <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'home' }">
      <button 
        class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
        @click="switchTab('home')">
        ホーム
      </button>
    </div>
    <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'bills' }">
      <button 
        class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
        @click="switchTab('apply')">
        シフト
      </button>
    </div>
    <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'bills' }">
      <button 
        class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
        @click="switchTab('customers')">
        顧客情報
      </button>
    </div>
  </nav>

  <div class="staff-mypage-page">
    <div class="staff-mypage mt-3">

      <div v-if="activeTab === 'home'"
        class="wrap">

        <!-- ランキング -->
        <div class="rank mb-5">
          <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
            <IconCrown />ランキング
          </h2>
          <RankingBlock :rows="monthlyRows" />
        </div>
        <!-- ▼ お店からのお知らせ -->
        <div class="notice mt-5">
          <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
            <IconInfoCircle />お知らせ
          </h2>

          <div v-if="notices.length" class="mb-4 bg-white">
            <div
              v-for="n in notices"
              :key="n.id"
              class="d-flex align-items-center justify-content-between p-3"
            >
              <!-- ▼ ここをリンク化して NewsDetail へ -->
              <RouterLink
                :to="{ name: 'news-detail', params: { id: n.id } }"
                class="d-flex flex-column"
              >
                <span class="text-muted small">
                  {{ dayjs(n.publish_at || n.created_at).format('YYYY/MM/DD') }}
                </span>
                <span v-if="n.pinned" class="badge bg-warning text-dark me-2">PIN</span>
                <strong>{{ n.title || n.message || '(無題)' }}</strong>
              </RouterLink>
            </div>
          </div>

          <p v-else class="text-muted d-flex align-items-center justify-content-center" style="min-height: 200px;">
            現在お知らせはありません
          </p>
        </div>
      </div>


      <!-- ▼ シフト申請 -->
      <div v-if="activeTab === 'apply'"
        class="mb-5"
      >
        <div class="mb-5">
          <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
            <IconCalendarPlus />シフト申請
          </h2>
          <div class="bg-white p-3">
            <div class="">
              <div class="row g-2">
              <div class="col-3 d-flex align-items-center">
                    <label class="form-label">開始日時</label>
              </div>
              <div class="col-9">
                  <input
                    v-model="form.start"
                    type="datetime-local"
                    class="form-control"
                  >
              </div>
              <div class="col-3 d-flex align-items-center">
                  <label class="form-label">終了日時</label>
              </div>
              <div class="col-9">
                  <input
                    v-model="form.end"
                    type="datetime-local"
                    class="form-control"
                  >
              </div>
              <div class="col-12 mt-4">
                <button
                  class="btn btn-outline-secondary w-100"
                  @click="addDraft"
                >
                  追加
                </button>
              </div>
            </div>
          </div>

          <div v-if="draftShifts.length" class="mt-3">
            <div v-for="(d,i) in draftShifts"
              class="box p-2 bg-white">
              <div class="time row border-bottom g-2 pb-2">
                <div class="col-4 align-items-center d-flex">
                  <div class="d-flex align-items-center gap-1">
                    <IconClock />
                    シフト{{ i+1 }}
                  </div>
                </div>
                <div class="col-7">
                  <div class="text-muted">{{ dayjs(d.plan_start).format('YYYY/MM/DD') }}</div>
                  <div class="fw-bold fs-4">
                    <span>{{ dayjs(d.plan_start).format('HH:mm') }}</span>〜<span>{{ dayjs(d.plan_end).format('HH:mm') }}</span>
                  </div>
                </div>
                <div class="col-1 df-center">
                  <button
                      @click="removeDraft(i)"
                    >
                      <IconX />
                  </button>                
                </div>
              </div>
            </div>
          </div>
          <div class="d-flex justify-content-center mt-3">
            <button
              class="btn btn-primary"
              :disabled="!draftShifts.length || submitting"
              @click="submitAll"
            >
              {{ draftShifts.length }} 件まとめて申請
            </button>
          </div>
        </div>
      </div>

        <div class="wrap">
          <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
            <IconListTree />シフト一覧
          </h2>
          <div class="search mb-3">
            <input 
              v-model="selectedMonth" 
              type="month" 
              class="form-control bg-white"
              placeholder="月を選択">
          </div>

          <div class="cards-container">
            <div
              v-for="s in filteredShifts"
              :key="s.id"
              class="card shift-card mb-3"
            >
              <div class="card-header d-flex align-items-center gap-2">

                  <IconClock />
                  <div>{{ dayjs(s.plan_start).format('YYYY/MM/DD') }}</div>
                  <div class="wrap fs-4">
                    <span class="fw-bold">{{ dayjs(s.plan_start).format('HH:mm') }}</span>〜<span class="fw-bold">{{ dayjs(s.plan_end).format('HH:mm') }}</span>
                  </div>

              </div>

              <div class="card-body">
                <div class="row g-2">
                  <div class="col-4 text-center">
                    <div class="badge bg-secondary">出勤</div>
                    <div class="fw-bold mt-1">{{ s.clock_in ? dayjs(s.clock_in).format('HH:mm') : '–' }}</div>
                  </div>
                  <div class="col-4 text-center">
                    <div class="badge bg-secondary">退勤</div>
                    <div class="fw-bold mt-1">{{ s.clock_out ? dayjs(s.clock_out).format('HH:mm') : '–' }}</div>
                  </div>
                  <div class="col-4 text-center">
                    <div class="badge bg-secondary">勤務時間</div>
                    <div class="fw-bold mt-1">{{ s.worked_min ? (s.worked_min/60).toFixed(2) + ' h' : '–' }}</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="!filteredShifts.length" class="text-center text-muted py-3">
              シフトがありません
            </div>
          </div>
        </div>

      </div>


      <!-- ▼ 顧客情報 -->
      <div v-if="activeTab === 'customers'">
        <h2 class="small fw-bold d-flex align-items-center justify-content-start gap-1 mb-2">
          <IconFaceId />顧客情報一覧</h2>
          <!-- 顧客情報一覧（絞り込み機能付き） -->
          <div class="wrap">
            <div class="row g-2 mb-3">
              <div class="col-6">
                <input v-model="customerSearch" class="form-control form-control-sm bg-white" placeholder="名前で検索">
              </div>
              <div class="col-3">
                <select v-model.number="customerMinVisit" class="form-select form-select-sm bg-white">
                  <option :value="0">来店条件なし</option>
                  <option :value="2">2回〜</option>
                  <option :value="3">3回〜</option>
                  <option :value="5">5回〜</option>
                  <option :value="10">10回〜</option>
                </select>
              </div>
              <div class="col-3">
                <select v-model="customerSort" class="form-select form-select-sm bg-white">
                  <option value="latest">最終来店順</option>
                  <option value="visits">来店回数順</option>
                </select>
              </div>
            </div>

            <div v-if="filteredAllCustomersList.length">
              <div v-for="c in filteredAllCustomersList" :key="c.name"
                @click="openCustomer(c.latestBillId)"
                class="card shadow-sm mb-3">
                <div class="card-header d-flex align-items-center justify-content-between">
                  <span class="fw-bold">{{ c.name }}様</span>
                  <span class="badge bg-secondary">来店{{ c.visitCount }}回</span>
                </div>
                <div class="card-body">
                  <div class="row g-2 small">
                    <div class="col-6">
                      <div class="text-muted">最終来店</div>
                      <div class="fw-bold">{{ dayjs(c.latestVisit).format('YYYY/MM/DD') }}</div>
                    </div>
                    <div class="col-6">
                      <div class="text-muted">ご利用金額</div>
                      <div class="fw-bold">{{ yen(c.latestSubtotal) }}</div>
                    </div>
                    <div v-if="c.casts.length" class="col-12">
                      <div class="text-muted">担当キャスト</div>
                      <div class="fw-bold">{{ c.casts.join(', ') }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <p v-else
              class="text-muted d-flex align-items-center justify-content-center"
              style="min-height: 200px;">
              顧客情報はまだありません
            </p>
          </div>
      </div>

      <CustomerDetailModal
        :bill-id="selectedBillId"
        :customer-stats="selectedCustomerStats"
        :show="showCustomerModal"
        @close="closeCustomerModal"
      />
    </div>
  </div>
</template>

<style>
.avatars img {
  width: 60px !important;
  height: 60px !important;
}
</style>
