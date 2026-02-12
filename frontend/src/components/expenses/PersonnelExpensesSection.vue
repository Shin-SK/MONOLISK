<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '@/api'
import { useUser } from '@/stores/useUser'
import {
  fetchPersonnelExpenseCategories,
  fetchPersonnelExpenses,
  createPersonnelExpense,
  createPersonnelExpenseSettlement,
  deletePersonnelExpense,
  attachPersonnelExpensesToPayrollRun,
} from '@/api'

const props = defineProps({
  runId: { type: Number, required: false, default: null },
  rangeFrom: { type: String, required: false, default: null },
  rangeTo: { type: String, required: false, default: null },
  allowAttach: { type: Boolean, default: false },
  subjectUserId: { type: [Number, String], default: null },
})

const userStore = useUser()

const categories = ref([])
const expenses = ref([]) // both collect + store_burden
const loading = ref(false)
const currentRole = computed(() => {
  return userStore.me?.current_role || userStore.info?.current_role || null
})
// Subject Search UI
const subjectQuery = ref('')
const subjectOptions = ref([]) // manager 用: [{ id, type: 'cast'|'staff', label }]
const subjectLoading = ref(false)
let subjectTimer = null

// Add Expense Modal
const showAddModal = ref(false)
const newExpenseForm = ref({
  subject_role: 'cast',
  subject_user_id: null,
  category_id: null,
  policy: 'collect', // 'collect' or 'store_burden'
  occurred_at: '',
  amount: 0,
  description: '',
})

// Settlement Modal (collect only)
const showSettlementModal = ref(false)
const selectedExpense = ref(null)
const settlementForm = ref({
  method: 'payroll_deduction',
  occurred_at: new Date().toISOString().split('T')[0],
  amount: 0,
  note: '',
})

const deletingId = ref(null)

const error = ref('')

function dbg(...args) {
  console.log("[PE]", ...args)
}

function currentRoleLabel() {
  const role = currentRole.value
  if (role === 'manager') return 'マネージャー'
  if (role === 'staff') return 'スタッフ'
  if (role === 'cast') return 'キャスト'
  return '不明'
}

function currentUserLabel() {
  const me = userStore.me || userStore.info || {}
  const name = me.stage_name
    || [me.last_name, me.first_name].filter(Boolean).join('')
    || me.username
    || 'unknown'
  return `${name}（${currentRoleLabel()}）`
}

function yen(n) {
  const num = Number(n || 0)
  return '¥' + num.toLocaleString('ja-JP')
}
function formatDate(dateStr) {
  if (!dateStr) return ''
  // ISO形式 (2025-12-25T00:00:00+09:00) から日付部分だけ取得
  const d = dateStr.split('T')[0]
  return d || dateStr
}
function getRemainingAmount(expense) {
  return Number(expense.amount || 0) - Number(expense.settled_amount || 0)
}
function isSettled(expense) {
  return expense.status === 'settled' || getRemainingAmount(expense) <= 0
}
function policyLabel(p) {
  return p === 'store_burden' ? '店舗負担' : '立替'
}

// manager 用: casts + staffs を全件取得して統合（検索なし）
const managerSelectOptions = ref([]) // [{ id, type: 'cast'|'staff', label }]
const managerSelected = ref(null) // 'cast:74' / 'staff:1'

async function fetchAllSubjectsForManager() {
  dbg("fetchAllSubjectsForManager: start")
  try {
    const [castsRes, staffsRes] = await Promise.all([
      api.get("/api/billing/casts/"),
      api.get("/api/billing/staffs/"),
    ])
    const casts = Array.isArray(castsRes.data)
      ? castsRes.data
      : Array.isArray(castsRes.data?.results)
        ? castsRes.data.results
        : []
    const staffs = Array.isArray(staffsRes.data)
      ? staffsRes.data
      : Array.isArray(staffsRes.data?.results)
        ? staffsRes.data.results
        : []
    const castOpts = casts.map((c) => ({
      user_id: c.user_id,
      type: 'cast',
      label: `${c.stage_name || c.name || c.username || 'キャスト'}（キャスト）`,
    }))
    const staffOpts = staffs.map((s) => ({
      user_id: s.user_id ?? s.id,
      type: 'staff',
      label: `${`${s.last_name || ''}${s.first_name || ''}`.trim() || s.username || 'スタッフ'}（スタッフ）`,
    }))
    managerSelectOptions.value = [...castOpts, ...staffOpts]
    dbg("fetchAllSubjectsForManager: loaded", { casts: casts.length, staffs: staffs.length, total: managerSelectOptions.value.length })
  } catch (e) {
    dbg("fetchAllSubjectsForManager: FAIL", { message: e?.message, status: e?.response?.status, data: e?.response?.data })
    managerSelectOptions.value = []
  }
}

watch(managerSelected, (val) => {
  if (!val) return
  const [type, idStr] = String(val).split(":")
  newExpenseForm.value.subject_role = type === 'staff' ? 'staff' : 'cast'
  newExpenseForm.value.subject_user_id = Number(idStr)
})

// 現在ロールに応じて対象者を初期化（cast/staffは自分、managerは未選択）
async function initializeSubjectByRole() {
  dbg("initializeSubjectByRole: currentRole", currentRole.value)
  const meUsername = userStore.me?.username || userStore.info?.username
  const meId = userStore.me?.id || userStore.info?.id
  if (!currentRole.value || !meUsername) {
    dbg("initializeSubjectByRole: missing role or username")
    return
  }
  if (currentRole.value === 'cast') {
    try {
      const res = await api.get("/api/billing/casts/", { params: { "user__username": meUsername } })
      const data = Array.isArray(res.data) ? res.data : Array.isArray(res.data?.results) ? res.data.results : []
      const me = data[0] || null
      if (me) {
        newExpenseForm.value.subject_role = 'cast'
        newExpenseForm.value.subject_user_id = me.user_id || meId
        subjectQuery.value = `${me.stage_name || me.username || '自分'}（キャスト）`
      }
      dbg("initializeSubjectByRole: cast self set", { id: newExpenseForm.value.subject_user_id })
    } catch (e) {
      dbg("initializeSubjectByRole: cast FAIL", { message: e?.message, status: e?.response?.status })
    }
    return
  }
  if (currentRole.value === 'staff') {
    try {
      const res = await api.get("/api/billing/staffs/", { params: { search: meUsername } })
      const data = Array.isArray(res.data) ? res.data : Array.isArray(res.data?.results) ? res.data.results : []
      const me = data[0] || null
      if (me) {
        newExpenseForm.value.subject_role = 'staff'
        // staff は User なので me.id を直接使用
        newExpenseForm.value.subject_user_id = meId
        subjectQuery.value = `${`${me.last_name || ''}${me.first_name || ''}`.trim() || me.username || '自分'}（スタッフ）`
      }
      dbg("initializeSubjectByRole: staff self set", { id: newExpenseForm.value.subject_user_id })
    } catch (e) {
      dbg("initializeSubjectByRole: staff FAIL", { message: e?.message, status: e?.response?.status })
    }
    return
  }
  if (currentRole.value === 'manager') {
    // 未選択状態で開始し、検索で対象者を選ばせる
    newExpenseForm.value.subject_role = 'cast' // デフォルト値だが選択時に上書きされる
    newExpenseForm.value.subject_user_id = null
    subjectQuery.value = ''
    managerSelected.value = null
    await fetchAllSubjectsForManager()
    dbg("initializeSubjectByRole: manager ready", { options: managerSelectOptions.value.length })
    return
  }
}

// 旧ロジックは廃止（subject_role=managerは存在しない）

async function loadData(force = false) {
  loading.value = true
  const bust = force ? { _ts: Date.now() } : {}
  try {
    const [cats, collectList, burdenList] = await Promise.all([
      fetchPersonnelExpenseCategories({ is_active: true, ...bust }),
      fetchPersonnelExpenses({ 
        policy: 'collect', 
        ...(props.runId ? { payroll_run: props.runId } : {}),
        ...(props.subjectUserId ? { subject_user: props.subjectUserId } : {}),
        ...bust,
      }),
      fetchPersonnelExpenses({ 
        policy: 'store_burden', 
        ...(props.runId ? { payroll_run: props.runId } : {}),
        ...(props.subjectUserId ? { subject_user: props.subjectUserId } : {}),
        ...bust,
      }),
    ])
    categories.value = Array.isArray(cats) ? cats : []
    const c = Array.isArray(collectList) ? collectList : []
    const b = Array.isArray(burdenList) ? burdenList : []
    // 結合＋発生日でソート
    expenses.value = [...c, ...b].sort((a, b) => String(a.occurred_at).localeCompare(String(b.occurred_at)))
  } catch (e) {
    console.error('[PersonnelExpensesSection] loadData failed', e)
  } finally {
    loading.value = false
  }
}

async function attachExpenses() {
  if (!props.allowAttach || !props.runId) return
  loading.value = true
  try {
    await attachPersonnelExpensesToPayrollRun(props.runId, {
      date_from: props.rangeFrom,
      date_to: props.rangeTo,
    })
    await loadData()
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || '取り込みに失敗しました'
  } finally {
    loading.value = false
  }
}

function openAddModal() {
  newExpenseForm.value = {
    subject_role: 'cast',
    subject_user_id: props.subjectUserId ?? (userStore.me?.id || userStore.info?.id || null),
    category_id: null,
    policy: 'collect',
    occurred_at: props.rangeFrom || '',
    amount: 0,
    description: '',
  }
  subjectQuery.value = ''
  subjectOptions.value = []
  showAddModal.value = true
  initializeSubjectByRole()
}
async function submitNewExpense() {
  if (!newExpenseForm.value.category_id || !newExpenseForm.value.subject_user_id) {
    error.value = '対象ユーザーとカテゴリを選択してください'
    return
  }
  try {
    await createPersonnelExpense({
      ...newExpenseForm.value,
      ...(props.runId ? { payroll_run: props.runId } : {}),
    })
    showAddModal.value = false
    await loadData(true)
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || '経費追加に失敗しました'
  }
}

function openSettlementModal(expense) {
  if (expense.policy === 'store_burden') return // 店舗負担は回収不可
  selectedExpense.value = expense
  settlementForm.value = {
    method: 'payroll_deduction',
    occurred_at: new Date().toISOString().split('T')[0],
    amount: getRemainingAmount(expense),
    note: '',
  }
  showSettlementModal.value = true
}
async function submitSettlement() {
  if (!selectedExpense.value) return
  try {
    await createPersonnelExpenseSettlement(selectedExpense.value.id, {
      amount: settlementForm.value.amount,
      settled_at: settlementForm.value.occurred_at,
      note: settlementForm.value.note,
    })
    showSettlementModal.value = false
    selectedExpense.value = null
    await loadData(true)
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || '回収登録に失敗しました'
  }
}

async function deleteExpense(expense) {
  if (!expense || !expense.id) return
  if (!window.confirm('この経費を削除しますか？')) return
  deletingId.value = expense.id
  try {
    await deletePersonnelExpense(expense.id)
    await loadData(true)
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || '削除に失敗しました'
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  dbg("mounted")
  dbg("api.baseURL =", api?.defaults?.baseURL)
  dbg("me =", userStore.me || userStore.info || null)
  dbg("currentRole(ref) set =", currentRole.value)

  loadData()
})
</script>

<template>
  <div class="mb-3">
    <div
      class="d-flex align-items-center"
      :class="currentRole === 'manager' ? 'justify-content-between' : 'justify-content-end'"
    >
      <div v-if="currentRole === 'manager'" class="py-3 fw-bold">経費申請</div>
      <div class="d-flex gap-2">
        <button v-if="allowAttach" class="btn btn-sm btn-outline-primary" @click="attachExpenses" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          対象期間から取り込む
        </button>
      </div>
    </div>

    <div v-if="expenses.length">
      <!-- manager: テーブル表示 -->
      <div class="table-responsive" v-if="currentRole === 'manager'">
        <table class="table table-striped table-hover mb-0">
          <thead>
            <tr>
              <th>発生日</th>
              <th>対象</th>
              <th>経費区分</th>
              <th>カテゴリ</th>
              <th>ステータス</th>
              <th>メモ</th>
              <th class="text-center">操作</th>
              <th class="text-end">金額</th>
              <th class="text-end">回収済</th>
              <th class="text-end">残高</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="exp in expenses" :key="exp.id">
              <td>{{ formatDate(exp.occurred_at) }}</td>
              <td>{{ exp.subject_user_display || exp.subject_user_id }}</td>
              <td>{{ policyLabel(exp.policy) }}</td>
              <td>{{ exp.category_name || exp.category_id }}</td>
              <td>
                <template v-if="exp.policy === 'store_burden'">
                  <span class="badge text-bg-secondary">店舗負担</span>
                </template>
                <template v-else>
                  <span v-if="isSettled(exp)" class="badge text-bg-success">回収済</span>
                  <span v-else class="badge text-bg-warning">未回収</span>
                </template>
              </td>
              <td class="text-truncate" style="max-width: 200px">{{ exp.description }}</td>
              <td class="text-center">
                <button
                  class="btn btn-sm btn-outline-primary"
                  @click="openSettlementModal(exp)"
                  :disabled="exp.policy === 'store_burden' || isSettled(exp)"
                >
                  回収
                </button>
              </td>
              <td class="text-end">{{ yen(exp.amount) }}</td>
              <td class="text-end">{{ yen(exp.settled_amount) }}</td>
              <td class="text-end">
                <span :class="{ 'text-danger fw-bold': getRemainingAmount(exp) > 0 }">
                  {{ yen(getRemainingAmount(exp)) }}
                </span>
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="table-light">
              <th colspan="7">合計</th>
              <th class="text-end">{{ yen(expenses.reduce((a, e) => a + Number(e.amount || 0), 0)) }}</th>
              <th class="text-end">{{ yen(expenses.reduce((a, e) => a + Number(e.settled_amount || 0), 0)) }}</th>
              <th class="text-end">{{ yen(expenses.reduce((a, e) => a + (Number(e.amount||0) - Number(e.settled_amount||0)), 0)) }}</th>
              <th colspan="3"></th>
            </tr>
          </tfoot>
        </table>
        <button class="btn btn-sm btn-primary" @click="openAddModal">
          <IconTextPlus />経費追加
        </button>
      </div>

      <!-- cast/staff: カード表示 -->
      <div v-else class="mt-1">
        <button class="btn btn-sm btn-primary mb-3" @click="openAddModal">
          <IconTextPlus />経費追加
        </button>
        <div v-for="exp in expenses" :key="exp.id">
          <div class="card mb-3 shadow-sm">
            <div class="card-header d-flex justify-content-between align-items-center">
              <span class="fw-bold">{{ exp.category_name || exp.category_id }}</span>
              <div class="wrap d-flex gap-2">
                <small class="fw-bold">{{ formatDate(exp.occurred_at) }}</small>
              <span class="badge" :class="exp.policy === 'store_burden' ? 'text-bg-secondary' : 'text-bg-primary'">
                {{ policyLabel(exp.policy) }}
              </span>                
                <span v-if="exp.policy === 'store_burden'" class="badge text-bg-secondary">店舗負担</span>
                <span v-else-if="isSettled(exp)" class="badge text-bg-success">回収済</span>
                <span v-else class="badge text-bg-warning">未回収</span>
                <button
                  class="text-danger small p-0"
                  @click="deleteExpense(exp)"
                  :disabled="deletingId === exp.id || loading"
                >
                  <IconTrash />
                </button>
              </div>
            </div>
            <div class="card-body row g-2">
              <div class="col-4 df-center flex-column">
                <div class="fw-bold small">金額</div>
                <div>{{ yen(exp.amount) }}</div>
              </div>
              <div class="col-4 df-center flex-column">
                <div class="fw-bold small">回収済</div>
                <div>{{ yen(exp.settled_amount) }}</div>
              </div>
              <div class="col-4 df-center flex-column">
                <div class="fw-bold small">残高</div>
                <div :class="{ 'text-danger': getRemainingAmount(exp) > 0 }">{{ yen(getRemainingAmount(exp)) }}</div>
              </div>
            </div>
            <div class="card-footer text-end" v-if="exp.description">
              <div class="col-12">
                <div class="df-center flex-column mb-1">
                  <span class="text-muted small">メモ</span>
                  <span class="text-truncate" style="max-width: 200px">{{ exp.description }}</span>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else>
      <div v-if="currentRole === 'manager'" class="card-body text-center text-muted">
        <p>この締めに紐づく経費はまだありません。</p>
        <p class="small">「対象期間から取り込む」で未紐付けの経費を一括取り込み、または「経費追加」で新規作成できます。</p>
      </div>
      <div v-else class="df-center py-5 px-3 bg-white rounded shadow-sm flex-column gap-3">
        <small class="text-muted">まだ経費が登録されていません。</small>
        <button class="btn btn-sm btn-primary" @click="openAddModal">
          <IconTextPlus />経費追加
        </button>
      </div>
    </div>
  </div>

  <!-- Add Expense Modal (policy selectable) -->
  <div class="modal fade" :class="{ show: showAddModal }" :style="{ display: showAddModal ? 'block' : 'none' }" tabindex="-1" v-if="showAddModal">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">経費を追加</h5>
          <button type="button" class="btn-close" @click="showAddModal = false"></button>
        </div>
        <div class="modal-body">
          <!-- 入力者情報（常時表示） -->
          <div class="mb-3">
            <label class="form-label">入力者</label>
            <div class="form-control-plaintext">
              {{ currentUserLabel() }}
            </div>
          </div>

          <!-- role 選択UIは廃止。currentRoleで自動制御 -->

          <div class="mb-3">
            <label class="form-label">対象ユーザー</label>

            <!-- manager: セレクト式（casts+staffsの全件） -->
            <template v-if="currentRole === 'manager'">
              <select class="form-select" v-model="managerSelected">
                <option :value="null">選択してください</option>
                <option
                  v-for="opt in managerSelectOptions"
                  :key="`${opt.type}-${opt.user_id}`"
                  :value="`${opt.type}:${opt.user_id}`"
                >
                  {{ opt.label }}
                </option>
              </select>
            </template>

            <!-- cast/staff: 自分のみ（変更不可） -->
            <template v-else>
              <div class="form-control-plaintext">{{ subjectQuery }}</div>
              <div class="form-text">このロールでは自分のみが対象です。</div>
            </template>
          </div>

          <div class="mb-3">
            <label class="form-label">カテゴリ</label>
            <select class="form-select" v-model.number="newExpenseForm.category_id">
              <option :value="null">選択してください</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.name }} ({{ cat.code }})
              </option>
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label">経費区分</label>
            <div class="d-flex gap-3">
              <div class="form-check">
                <input class="form-check-input" type="radio" id="expPolicyCollect" value="collect" v-model="newExpenseForm.policy" />
                <label class="form-check-label" for="expPolicyCollect">立替（回収する）</label>
              </div>
              <div class="form-check">
                <input class="form-check-input" type="radio" id="expPolicyBurden" value="store_burden" v-model="newExpenseForm.policy" />
                <label class="form-check-label" for="expPolicyBurden">店舗負担（回収しない）</label>
              </div>
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label">発生日</label>
            <input type="date" class="form-control" v-model="newExpenseForm.occurred_at" />
          </div>

          <div class="mb-3">
            <label class="form-label">金額</label>
            <input type="number" class="form-control" v-model.number="newExpenseForm.amount" />
          </div>

          <div class="mb-3">
            <label class="form-label">メモ</label>
            <textarea class="form-control" v-model="newExpenseForm.description" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-sm btn-secondary" @click="showAddModal = false">キャンセル</button>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            @click="submitNewExpense"
            :disabled="!newExpenseForm.category_id || !newExpenseForm.subject_user_id || (currentRole === 'manager' && !managerSelected)"
          >
            追加
          </button>
        </div>
      </div>
    </div>
  </div>
  <div class="modal-backdrop fade" :class="{ show: showAddModal }" v-if="showAddModal"></div>

  <!-- Settlement Modal -->
  <div class="modal fade" :class="{ show: showSettlementModal }" :style="{ display: showSettlementModal ? 'block' : 'none' }" tabindex="-1" v-if="showSettlementModal">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">立替を回収</h5>
          <button type="button" class="btn-close" @click="showSettlementModal = false"></button>
        </div>
        <div class="modal-body">
          <div class="alert alert-info" v-if="selectedExpense">
            <div class="small"><strong>対象経費:</strong> {{ selectedExpense.category_name }} - {{ selectedExpense.subject_user_display }}</div>
            <div class="small"><strong>残高:</strong> {{ yen(getRemainingAmount(selectedExpense)) }}</div>
          </div>

          <div class="mb-3">
            <label class="form-label">回収方法</label>
            <select class="form-select" v-model="settlementForm.method">
              <option value="payroll_deduction">給与天引き</option>
              <option value="cash">現金回収</option>
            </select>
            <div class="form-text">給与天引きの場合は、この締めに紐づけられます。現金回収の場合は締めとは独立して記録されます。</div>
          </div>

          <div class="mb-3">
            <label class="form-label">回収日</label>
            <input type="date" class="form-control" v-model="settlementForm.occurred_at" />
          </div>

          <div class="mb-3">
            <label class="form-label">回収額</label>
            <input type="number" class="form-control" v-model.number="settlementForm.amount" />
            <div class="form-text">残高以下の金額で部分回収も可能です。</div>
          </div>

          <div class="mb-3">
            <label class="form-label">メモ</label>
            <textarea class="form-control" v-model="settlementForm.note" rows="2" placeholder="例: 給与から天引き、現金で回収 など"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="showSettlementModal = false">キャンセル</button>
          <button type="button" class="btn btn-primary" @click="submitSettlement">回収を記録</button>
        </div>
      </div>
    </div>
  </div>
  <div class="modal-backdrop fade" :class="{ show: showSettlementModal }" v-if="showSettlementModal"></div>
</template>

<style scoped>
.table-responsive{ th, td{ white-space: nowrap; } }
.modal.show { display: block !important; }
.modal-backdrop.show { opacity: 0.5; }
</style>
