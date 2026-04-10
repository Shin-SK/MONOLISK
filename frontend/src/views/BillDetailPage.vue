<script setup>
import { ref, reactive, onMounted, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
  fetchBill, fetchBillEditLogs, createBillEditLog, fetchMasters,
  fetchCasts, fetchCustomers,
  patchBill, addBillItem, patchBillItem, deleteBillItem, deleteBill,
} from '@/api'
import PayrollSnapshotPanel from '@/components/expenses/PayrollSnapshotPanel.vue'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)

// ── 閲覧モード ──
const bill = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const editLogs = ref([])
const showLogs = ref(false)

// ── 編集モード ──
const editing = ref(false)
const saving = ref(false)
const editItems = ref([])       // { _key, id?, item_master_id?, name, price, qty, served_by_cast_id, customer_id, _delete }
const editPaidCash = ref(0)
const editPaidCard = ref(0)
const editMemo = ref('')

// ── キャスト・顧客リスト ──
const casts = ref([])
const customers = ref([])

// ── 品目サジェスト ──
const masters = ref([])
const addQuery = ref('')
const showSuggest = ref(false)
const filteredMasters = computed(() => {
  const q = (addQuery.value || '').trim().toLowerCase()
  if (!q) return masters.value.slice(0, 30)
  return masters.value.filter(m =>
    (m.name || '').toLowerCase().includes(q) ||
    (m.code || '').toLowerCase().includes(q)
  ).slice(0, 30)
})

// ── ヘルパー ──
const yen  = n => `¥${(Number(n||0)).toLocaleString()}`
const dt   = s => s ? dayjs(s).format('YYYY/MM/DD HH:mm') : '—'
const stayLabel = t => ({ nom: '本指名', in: '場内', free: 'フリー', dohan: '同伴' }[t] || t)

const payrollSnapshot = computed(() => {
  const b = bill.value || {}
  return b.payroll_snapshot || b.payrollSnapshot || null
})
const payrollDirty = computed(() => {
  const b = bill.value || {}
  return b.payroll_dirty ?? b.payrollSnapshotDirty ?? false
})

// ── 編集モードの小計計算 ──
const editSubtotal = computed(() =>
  editItems.value
    .filter(it => !it._delete)
    .reduce((s, it) => s + (Number(it.price) || 0) * (Number(it.qty) || 0), 0)
)

// ── ロード ──
async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    bill.value = await fetchBill(id)
  } catch (e) {
    console.error(e); errorMsg.value = '伝票が見つかりません'
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  try { editLogs.value = await fetchBillEditLogs(id) } catch (e) { console.error(e) }
}

async function loadMasters() {
  try { masters.value = await fetchMasters() } catch (e) { console.error(e) }
}
async function loadCasts() {
  try { casts.value = await fetchCasts() } catch (e) { console.error(e) }
}
async function loadCustomers() {
  try {
    const res = await fetchCustomers()
    customers.value = res.results ?? res
  } catch (e) { console.error(e) }
}

// ── 編集開始 ──
function startEdit() {
  const b = bill.value
  if (!b) return
  editItems.value = (b.items || []).map((it, i) => ({
    _key: `existing-${it.id}`,
    id: it.id,
    item_master_id: it.item_master?.id || null,
    name: it.item_master?.name || it.name,
    price: it.price,
    qty: it.qty,
    served_by_cast_id: it.served_by_cast?.id || null,
    customer_id: it.customer?.id || null,
    _delete: false,
  }))
  editPaidCash.value = b.paid_cash || 0
  editPaidCard.value = b.paid_card || 0
  editMemo.value = b.memo || ''
  editing.value = true
  if (!masters.value.length) loadMasters()
  if (!casts.value.length) loadCasts()
  if (!customers.value.length) loadCustomers()
}

function cancelEdit() {
  editing.value = false
}

// ── 品目追加 ──
let addKeySeq = 0
function selectMaster(m) {
  editItems.value.push({
    _key: `new-${++addKeySeq}`,
    id: null,
    item_master_id: m.id,
    name: m.name,
    price: m.price_regular || 0,
    qty: 1,
    served_by_cast_id: null,
    customer_id: null,
    _delete: false,
  })
  addQuery.value = ''
  showSuggest.value = false
}

function addFreeItem() {
  editItems.value.push({
    _key: `new-${++addKeySeq}`,
    id: null,
    item_master_id: null,
    name: addQuery.value || '手入力品目',
    price: 0,
    qty: 1,
    served_by_cast_id: null,
    customer_id: null,
    _delete: false,
  })
  addQuery.value = ''
  showSuggest.value = false
}

// ── 一括保存 ──
async function saveAll() {
  saving.value = true
  try {
    const b = bill.value
    const origItems = b.items || []

    // ★ 変更前のスナップショットをdiffとして記録用にまとめる
    const logDiff = { items: [], bill: {} }

    // 1. 削除対象（既存IDがあり _delete=true）
    const toDelete = editItems.value.filter(it => it.id && it._delete)
    for (const it of toDelete) {
      await deleteBillItem(id, it.id)
      logDiff.items.push({ action: '削除', name: it.name, price: it.price, qty: it.qty })
    }

    // 2. 新規追加（idがない、_delete=false）
    const toAdd = editItems.value.filter(it => !it.id && !it._delete)
    for (const it of toAdd) {
      const payload = { name: it.name, price: Number(it.price), qty: Number(it.qty) }
      if (it.item_master_id) payload.item_master = it.item_master_id
      if (it.served_by_cast_id) payload.served_by_cast_id = it.served_by_cast_id
      if (it.customer_id) payload.customer_id = it.customer_id
      await addBillItem(id, payload)
      logDiff.items.push({ action: '追加', name: it.name, price: Number(it.price), qty: Number(it.qty) })
    }

    // 3. 変更対象（既存IDがあり、値が変わっている）
    const toUpdate = editItems.value.filter(it => it.id && !it._delete)
    for (const it of toUpdate) {
      const orig = origItems.find(o => o.id === it.id)
      if (!orig) continue
      const diff = {}
      const itemLog = { action: '変更', name: it.name }
      let changed = false
      if (Number(it.price) !== Number(orig.price)) {
        diff.price = Number(it.price)
        itemLog.price = { old: orig.price, new: Number(it.price) }
        changed = true
      }
      if (Number(it.qty) !== Number(orig.qty)) {
        diff.qty = Number(it.qty)
        itemLog.qty = { old: orig.qty, new: Number(it.qty) }
        changed = true
      }
      const origCastId = orig.served_by_cast?.id || null
      const newCastId = it.served_by_cast_id || null
      if (newCastId !== origCastId) {
        diff.served_by_cast_id = newCastId
        const castName = casts.value.find(c => c.id === newCastId)?.stage_name || '—'
        const origName = orig.served_by_cast?.stage_name || '—'
        itemLog.cast = { old: origName, new: castName }
        changed = true
      }
      const origCustId = orig.customer?.id || null
      const newCustId = it.customer_id || null
      if (newCustId !== origCustId) {
        diff.customer_id = newCustId
        changed = true
      }
      if (changed) {
        await patchBillItem(id, it.id, diff)
        logDiff.items.push(itemLog)
      }
    }

    // 4. 伝票本体の変更（支払い・メモ）
    const billPatch = {}
    if (Number(editPaidCash.value) !== Number(b.paid_cash || 0)) {
      billPatch.paid_cash = Number(editPaidCash.value)
      logDiff.bill.paid_cash = { old: b.paid_cash || 0, new: Number(editPaidCash.value) }
    }
    if (Number(editPaidCard.value) !== Number(b.paid_card || 0)) {
      billPatch.paid_card = Number(editPaidCard.value)
      logDiff.bill.paid_card = { old: b.paid_card || 0, new: Number(editPaidCard.value) }
    }
    if (editMemo.value !== (b.memo || '')) {
      billPatch.memo = editMemo.value
      logDiff.bill.memo = { old: b.memo || '', new: editMemo.value }
    }
    if (Object.keys(billPatch).length) {
      await patchBill(id, billPatch)
    }

    // 5. 変更があればまとめて1件のログを記録
    const hasChanges = logDiff.items.length || Object.keys(logDiff.bill).length
    if (hasChanges) {
      await createBillEditLog(id, 'edit', logDiff)
    }

    // 6. リロード
    await load()
    await loadLogs()
    editing.value = false
  } catch (e) {
    console.error(e)
    errorMsg.value = '保存に失敗しました: ' + (e?.response?.data?.detail || e.message || e)
  } finally {
    saving.value = false
  }
}

// ── 編集履歴 ──
function actionLabel(action) {
  return { edit: '編集', patch_bill: '伝票変更', add_item: '明細追加', patch_item: '明細変更', delete_item: '明細削除' }[action] || action
}
function formatDiff(diff) {
  if (!diff) return ''
  const parts = []

  // 新形式（一括diff）
  if (diff.items && Array.isArray(diff.items)) {
    for (const it of diff.items) {
      const detail = []
      if (it.price && typeof it.price === 'object') detail.push(`単価: ${it.price.old}→${it.price.new}`)
      if (it.qty && typeof it.qty === 'object') detail.push(`数量: ${it.qty.old}→${it.qty.new}`)
      parts.push(`[${it.action}] ${it.name}${detail.length ? ' (' + detail.join(', ') + ')' : ''}`)
    }
  }
  if (diff.bill && typeof diff.bill === 'object') {
    for (const [k, v] of Object.entries(diff.bill)) {
      if (v && typeof v === 'object' && 'old' in v && 'new' in v) parts.push(`${k}: ${v.old} → ${v.new}`)
    }
  }

  // 旧形式（個別diff、既存ログ互換）
  if (!diff.items && !diff.bill) {
    for (const [k, v] of Object.entries(diff)) {
      if (k === 'item_id') continue
      if (v && typeof v === 'object' && 'old' in v && 'new' in v) parts.push(`${k}: ${v.old} → ${v.new}`)
      else parts.push(`${k}: ${v}`)
    }
  }

  return parts.join(' / ')
}

// ── 伝票削除 ──
const deleting = ref(false)
async function removeBill() {
  if (!confirm(`伝票 #${id} を削除しますか？この操作は元に戻せません。`)) return
  deleting.value = true
  try {
    await deleteBill(id)
    router.push({ name: route.name?.startsWith('Staff') ? 'StaffBillList' : 'BillList' })
  } catch (e) {
    console.error(e)
    errorMsg.value = '削除に失敗しました: ' + (e?.response?.data?.detail || e.message || e)
  } finally {
    deleting.value = false
  }
}

onMounted(() => { load(); loadLogs() })
</script>

<template>
  <div class="container-fluid py-3">
    <div class="d-flex align-items-center justify-content-between mb-2">
      <h1 class="h5 mb-0">伝票 #{{ id }}</h1>
      <div class="d-flex gap-2">
        <template v-if="!editing">
          <button class="btn btn-primary btn-sm" @click="startEdit">編集</button>
          <button class="btn btn-outline-danger btn-sm" :disabled="deleting" @click="removeBill">
            {{ deleting ? '削除中…' : '削除' }}
          </button>
        </template>
        <template v-else>
          <button class="btn btn-success btn-sm" :disabled="saving" @click="saveAll">
            {{ saving ? '保存中…' : '保存' }}
          </button>
          <button class="btn btn-outline-secondary btn-sm" :disabled="saving" @click="cancelEdit">キャンセル</button>
        </template>
        <button class="btn btn-outline-secondary btn-sm" @click="router.back()">戻る</button>
      </div>
    </div>

    <div v-if="errorMsg" class="alert alert-danger alert-dismissible">
      {{ errorMsg }}
      <button type="button" class="btn-close" @click="errorMsg = ''"></button>
    </div>
    <div v-if="loading">Loading…</div>

    <div v-if="bill" class="card">
      <div class="card-body">
        <!-- ヘッダ情報（表示のみ） -->
        <div class="row g-3">
          <div class="col-md-3"><small class="text-muted">卓</small><div class="fw-bold">{{ bill.table?.name || '—' }}</div></div>
          <div class="col-md-3"><small class="text-muted">クローズ</small><div class="fw-bold">{{ dt(bill.closed_at) }}</div></div>
          <div class="col-md-3">
            <small class="text-muted">支払(現金)</small>
            <div v-if="!editing" class="fw-bold">{{ yen(bill.paid_cash) }}</div>
            <input v-else type="number" class="form-control form-control-sm" v-model.number="editPaidCash" min="0">
          </div>
          <div class="col-md-3">
            <small class="text-muted">支払(カード)</small>
            <div v-if="!editing" class="fw-bold">{{ yen(bill.paid_card) }}</div>
            <input v-else type="number" class="form-control form-control-sm" v-model.number="editPaidCard" min="0">
          </div>
        </div>

        <!-- 担当キャスト -->
        <div v-if="bill.stays && bill.stays.length" class="row g-3 mt-1">
          <div class="col-12">
            <small class="text-muted">担当キャスト</small>
            <div class="d-flex flex-wrap gap-2 mt-1">
              <span v-for="s in bill.stays" :key="s.cast?.id + '-' + s.stay_type"
                    class="badge"
                    :class="{
                      'bg-primary': s.stay_type === 'nom',
                      'bg-success': s.stay_type === 'in',
                      'bg-info text-dark': s.stay_type === 'free',
                      'bg-warning text-dark': s.stay_type === 'dohan',
                    }">
                {{ s.cast?.stage_name || '—' }}
                <small class="ms-1">{{ stayLabel(s.stay_type) }}</small>
              </span>
            </div>
          </div>
        </div>

        <hr>

        <!-- ===== 閲覧モード ===== -->
        <template v-if="!editing">
          <h6 class="mb-2">明細</h6>
          <div class="table-responsive">
            <table class="table table-sm align-middle">
              <thead>
                <tr><th>ID</th><th>品目</th><th>担当</th><th>顧客</th><th class="text-end">単価</th><th class="text-end">数量</th><th class="text-end">小計</th></tr>
              </thead>
              <tbody>
                <tr v-for="it in bill.items || []" :key="it.id">
                  <td>#{{ it.id }}</td>
                  <td>{{ it.item_master?.name || it.name }}</td>
                  <td>{{ it.served_by_cast?.stage_name || '—' }}</td>
                  <td>{{ it.customer?.name || '—' }}</td>
                  <td class="text-end">{{ yen(it.price) }}</td>
                  <td class="text-end">{{ it.qty }}</td>
                  <td class="text-end">{{ yen((it.price||0) * (it.qty||0)) }}</td>
                </tr>
                <tr v-if="!bill.items?.length"><td colspan="7" class="text-muted">明細なし</td></tr>
              </tbody>
              <tfoot>
                <tr><th colspan="6" class="text-end">小計</th><th class="text-end">{{ yen(bill.subtotal) }}</th></tr>
                <tr><th colspan="6" class="text-end">サービス</th><th class="text-end">{{ yen(bill.service_amount) }}</th></tr>
                <tr><th colspan="6" class="text-end">税</th><th class="text-end">{{ yen(bill.tax_amount) }}</th></tr>
                <tr><th colspan="6" class="text-end">合計</th><th class="text-end fw-bold">{{ yen(bill.grand_total ?? bill.total) }}</th></tr>
              </tfoot>
            </table>
          </div>

          <!-- メモ -->
          <div v-if="bill.memo" class="mt-2">
            <small class="text-muted">メモ</small>
            <div>{{ bill.memo }}</div>
          </div>
        </template>

        <!-- ===== 編集モード ===== -->
        <template v-else>
          <h6 class="mb-2">明細 <small class="text-muted">（編集中）</small></h6>
          <div class="table-responsive">
            <table class="table table-sm align-middle">
              <thead>
                <tr>
                  <th>品目</th>
                  <th style="width:130px">担当</th>
                  <th style="width:130px">顧客</th>
                  <th class="text-end" style="width:110px">単価</th>
                  <th class="text-end" style="width:70px">数量</th>
                  <th class="text-end" style="width:90px">小計</th>
                  <th style="width:40px"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in editItems" :key="it._key"
                    :class="{ 'table-danger text-decoration-line-through opacity-50': it._delete }">
                  <td>{{ it.name }}</td>
                  <td>
                    <select v-if="!it._delete" class="form-select form-select-sm"
                            v-model="it.served_by_cast_id">
                      <option :value="null">—</option>
                      <option v-for="c in casts" :key="c.id" :value="c.id">{{ c.stage_name }}</option>
                    </select>
                    <span v-else>—</span>
                  </td>
                  <td>
                    <select v-if="!it._delete" class="form-select form-select-sm"
                            v-model="it.customer_id">
                      <option :value="null">—</option>
                      <option v-for="cu in customers" :key="cu.id" :value="cu.id">{{ cu.display_name || cu.full_name || `#${cu.id}` }}</option>
                    </select>
                    <span v-else>—</span>
                  </td>
                  <td class="text-end">
                    <input v-if="!it._delete" type="number" class="form-control form-control-sm text-end"
                           v-model.number="it.price" min="0">
                    <span v-else>{{ yen(it.price) }}</span>
                  </td>
                  <td class="text-end">
                    <input v-if="!it._delete" type="number" class="form-control form-control-sm text-end"
                           v-model.number="it.qty" min="1" max="99">
                    <span v-else>{{ it.qty }}</span>
                  </td>
                  <td class="text-end">{{ yen((Number(it.price)||0) * (Number(it.qty)||0)) }}</td>
                  <td class="text-center">
                    <button v-if="!it._delete" class="btn btn-outline-danger btn-sm px-1 py-0"
                            @click="it._delete = true" title="削除">✕</button>
                    <button v-else class="btn btn-outline-secondary btn-sm px-1 py-0"
                            @click="it._delete = false" title="元に戻す">↩</button>
                  </td>
                </tr>
              </tbody>
              <tfoot>
                <tr><th colspan="5" class="text-end">小計</th><th class="text-end">{{ yen(editSubtotal) }}</th><th></th></tr>
              </tfoot>
            </table>
          </div>

          <!-- 品目追加 -->
          <div class="mt-2 position-relative" style="max-width:400px">
            <div class="input-group input-group-sm">
              <input type="text" class="form-control" placeholder="品目を検索して追加…"
                     v-model="addQuery"
                     @focus="showSuggest = true"
                     @blur="setTimeout(() => showSuggest = false, 200)">
              <button class="btn btn-outline-secondary" @click="addFreeItem" title="手入力で追加">手入力</button>
            </div>
            <div v-if="showSuggest && filteredMasters.length"
                 class="list-group position-absolute w-100 shadow-sm" style="z-index:10; max-height:240px; overflow-y:auto">
              <button v-for="m in filteredMasters" :key="m.id"
                      class="list-group-item list-group-item-action py-1 d-flex justify-content-between"
                      @mousedown.prevent="selectMaster(m)">
                <span>{{ m.name }}</span>
                <small class="text-muted">{{ yen(m.price_regular) }}</small>
              </button>
            </div>
          </div>

          <!-- メモ -->
          <div class="mt-3">
            <small class="text-muted">メモ</small>
            <textarea class="form-control form-control-sm" rows="2" v-model="editMemo"></textarea>
          </div>
        </template>

        <!-- 立替明細（表示のみ） -->
        <div v-if="bill.substitute_items && bill.substitute_items.length" class="mt-4">
          <h6 class="mb-2">立替明細</h6>
          <div class="table-responsive">
            <table class="table table-sm align-middle">
              <thead>
                <tr><th>商品</th><th class="text-center">数量</th><th>キャスト</th><th>顧客</th><th class="text-end">立替額</th></tr>
              </thead>
              <tbody>
                <tr v-for="si in bill.substitute_items" :key="si.id">
                  <td>{{ si.item_master?.name || si.name }}</td>
                  <td class="text-center">{{ si.qty }}</td>
                  <td>{{ si.cast?.stage_name || '—' }}</td>
                  <td>{{ si.customer?.name || '—' }}</td>
                  <td class="text-end">{{ yen(si.substitute_amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 給与計算セクション: 現在非表示（復活の可能性あり）
        <div class="mt-4">
          <PayrollSnapshotPanel
            :snapshot="payrollSnapshot"
            :dirty="payrollDirty"
            :bill-id="bill?.id"
          />
        </div>
        -->

        <!-- 編集履歴 -->
        <div v-if="editLogs.length" class="mt-4">
          <h6 class="mb-2" style="cursor:pointer" @click="showLogs = !showLogs">
            編集履歴 ({{ editLogs.length }})
            <small class="text-muted">{{ showLogs ? '▲' : '▼' }}</small>
          </h6>
          <div v-if="showLogs" class="table-responsive">
            <table class="table table-sm table-bordered align-middle">
              <thead class="table-light">
                <tr><th>日時</th><th>操作</th><th>変更内容</th><th>ユーザー</th></tr>
              </thead>
              <tbody>
                <tr v-for="log in editLogs" :key="log.id">
                  <td class="text-nowrap">{{ dt(log.created_at) }}</td>
                  <td>{{ actionLabel(log.action) }}</td>
                  <td><small>{{ formatDiff(log.diff) }}</small></td>
                  <td>{{ log.username || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
