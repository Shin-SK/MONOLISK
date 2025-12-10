<script setup>
import { ref, watch, computed } from 'vue'
import dayjs from 'dayjs'
import { fetchBill, fetchCustomer, fetchBillItemsByBillId, updateCustomer } from '@/api'

const props = defineProps({
  billId: { type: Number, default: null },
  show:   { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const loading   = ref(false)
const bill      = ref(null)
const customer  = ref(null)
const billItems = ref([])
const errorMsg  = ref('')
const activeTab = ref('customer') // 'customer' | 'bill'
const isEditing = ref(false)
const editForm  = ref({
  display_name: '',
  phone: '',
  memo: ''
})
const saving = ref(false)

// 日付等の表示
const openedAt = computed(() =>
  bill.value?.opened_at ? dayjs(bill.value.opened_at).format('YYYY/MM/DD HH:mm') : '—'
)

// 合計の表示（存在するキーを優先）
const totals = computed(() => {
  const b = bill.value || {}
  const toNum = v => (typeof v === 'number' ? v : (v ? Number(v) : 0)) || 0
  return {
    subtotal:     toNum(b.subtotal),
    service:      toNum(b.service_charge ?? b.service ?? 0),
    tax:          toNum(b.tax),
    grand_total:  toNum(b.grand_total ?? b.total ?? (toNum(b.subtotal)+toNum(b.service_charge)+toNum(b.tax))),
    paid_total:   toNum(b.paid_total),
  }
})

// アイテム行のフォールバック整形（name/qty/unit/line）
function normalizeItem(it) {
  const name = it?.name ?? it?.item_name ?? it?.master?.name ?? it?.item?.name ?? '(不明)'
  const qty  = it?.quantity ?? it?.qty ?? it?.count ?? 1
  const unit = it?.unit_price ?? it?.price ?? it?.unit ?? 0
  const line = it?.total ?? (Number(unit) * Number(qty) || 0)
  return { id: it?.id, name, qty, unit, line, route: it?.route || it?.route_code || null }
}

async function loadDetail () {
  if (!props.billId) return
  loading.value  = true
  errorMsg.value = ''
  bill.value     = null
  customer.value = null
  billItems.value = []
  try {
    const b = await fetchBill(props.billId)
    bill.value = b

    // 顧客詳細
    const cid = b.customer_id || b.customer?.id
    if (cid) customer.value = await fetchCustomer(cid)

    // 明細：bill.items があればそれ、無ければ /bill-items?bill=ID
    let items = []
    if (Array.isArray(b.items) && b.items.length) {
      items = b.items
    } else {
      items = await fetchBillItemsByBillId(props.billId)
    }
    billItems.value = items.map(normalizeItem)
  } catch (e) {
    console.error(e)
    errorMsg.value = '詳細の取得に失敗しました'
  } finally {
    loading.value = false
  }
}

watch(() => props.billId, () => { if (props.show) loadDetail() })
watch(() => props.show,   (v) => { if (v && props.billId) loadDetail() })
watch(() => isEditing.value, (editing) => {
  if (editing) {
    const name = customer.value?.full_name 
      || customer.value?.display_name 
      || bill.value?.customer_display_name 
      || ''
    const phone = customer.value?.phone || ''
    const memo = customer.value?.memo || ''
    
    editForm.value = {
      display_name: name,
      phone: phone,
      memo: memo
    }
    console.log('Edit form initialized:', editForm.value)
  }
})

function close () { 
  isEditing.value = false
  emit('close') 
}
function setTab(t){ activeTab.value = t }

function startEdit() {
  console.log('startEdit called', customer.value)
  if (!customer.value) return
  editForm.value = {
    display_name: customer.value.display_name || '',
    phone: customer.value.phone || '',
    memo: customer.value.memo || ''
  }
  isEditing.value = true
  console.log('isEditing set to', isEditing.value)
}

function cancelEdit() {
  isEditing.value = false
}

async function saveEdit() {
  console.log('saveEdit called', { customer: customer.value, bill: bill.value })
  
  const customerId = customer.value?.id 
    || bill.value?.customer_id 
    || bill.value?.customer?.id
    || (bill.value?.customers && bill.value.customers[0]?.id)
  
  console.log('Customer ID:', customerId)
  
  if (!customerId) {
    console.log('No customer ID found')
    errorMsg.value = '顧客IDが取得できませんでした'
    return
  }
  console.log('Starting save...', editForm.value)
  saving.value = true
  errorMsg.value = ''
  try {
    const updated = await updateCustomer(customerId, {
      full_name: editForm.value.display_name,
      phone: editForm.value.phone,
      memo: editForm.value.memo
    })
    console.log('Updated:', updated)
    customer.value = updated
    isEditing.value = false
  } catch (e) {
    console.error('Save error:', e)
    errorMsg.value = '保存に失敗しました'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div
    class="modal fade show"
    :style="{ display: show ? 'block' : 'none', background: 'rgba(0,0,0,0.5)' }"
    role="dialog"
    aria-modal="true"
    v-if="show"
    @click.self="close"
  >
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <div class="modal-content">

        <div class="modal-header">
          <h5 class="modal-title">
            顧客詳細
            <small v-if="customer?.display_name" class="text-muted ms-2">/ {{ customer.display_name }}</small>
          </h5>
          <button type="button" class="btn-close" @click="close" aria-label="Close"></button>
        </div>

        <div class="modal-body">
          <div v-if="loading" class="text-center py-3">読み込み中…</div>
          <div v-else-if="errorMsg" class="alert alert-danger">{{ errorMsg }}</div>
          <template v-else>
            <!-- タブ -->
            <ul class="nav nav-tabs mb-3">
              <li class="nav-item">
                <button class="nav-link" :class="{ active: activeTab==='customer' }" @click="setTab('customer')">
                  顧客情報
                </button>
              </li>
              <li class="nav-item">
                <button class="nav-link" :class="{ active: activeTab==='bill' }" @click="setTab('bill')">
                  このときの伝票
                </button>
              </li>
            </ul>

            <!-- 顧客情報タブ -->
            <div v-if="activeTab==='customer'">
              <div v-if="!isEditing">
                <dl class="row mb-0">
                  <dt class="col-4">来店日時</dt>
                  <dd class="col-8">{{ openedAt }}</dd>

                  <dt class="col-4">顧客名</dt>
                  <dd class="col-8">{{ customer?.full_name || customer?.display_name || bill?.customer_display_name || '—' }}</dd>

                  <dt class="col-4">電話</dt>
                  <dd class="col-8">{{ customer?.phone || '—' }}</dd>

                  <dt class="col-4">メモ</dt>
                  <dd class="col-8">
                    <pre class="mb-0" style="white-space:pre-wrap">{{ customer?.memo || '—' }}</pre>
                  </dd>

                  <dt class="col-4">来店回数</dt>
                  <dd class="col-8">{{ customer?.visit_count ?? '—' }}</dd>

                  <dt class="col-4">直近来店</dt>
                  <dd class="col-8">
                    <span v-if="customer?.last_visit_at">
                      {{ dayjs(customer.last_visit_at).format('YYYY/MM/DD') }}
                    </span>
                    <span v-else>—</span>
                  </dd>
                </dl>
                <button type="button" class="btn btn-primary btn-sm" @click="isEditing = true">編集</button>
              </div>

              <div v-else>
                <div class="mb-3">
                  <label class="form-label">顧客名</label>
                  <input type="text" class="form-control" v-model="editForm.display_name">
                </div>
                <div class="mb-3">
                  <label class="form-label">電話</label>
                  <input type="text" class="form-control" v-model="editForm.phone">
                </div>
                <div class="mb-3">
                  <label class="form-label">メモ</label>
                  <textarea class="form-control" rows="4" v-model="editForm.memo"></textarea>
                </div>
                <div class="d-flex gap-2">
                  <button type="button" class="btn btn-primary" @click="saveEdit" :disabled="saving">
                    {{ saving ? '保存中...' : '保存' }}
                  </button>
                  <button type="button" class="btn btn-secondary" @click="cancelEdit" :disabled="saving">キャンセル</button>
                </div>
              </div>
            </div>

            <!-- このときの伝票タブ -->
            <div v-show="activeTab==='bill'">
              <div class="d-flex justify-content-between align-items-center mb-2 small text-muted">
                <span>伝票 #{{ bill?.id ?? '—' }}</span>
                <span>来店：{{ openedAt }}</span>
              </div>

              <div class="table-responsive">
                <table class="table table-sm align-middle text-nowrap">
                  <thead class="table-light">
                    <tr>
                      <th>品目</th>
                      <th class="text-center" style="width:6em;">数量</th>
                      <th class="text-end"   style="width:8em;">単価</th>
                      <th class="text-end"   style="width:8em;">金額</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="it in billItems" :key="it.id || it.name">
                      <td>
                        <div class="fw-bold">{{ it.name }}</div>
                        <div v-if="it.route" class="text-muted small">route: {{ it.route }}</div>
                      </td>
                      <td class="text-center">{{ it.qty }}</td>
                      <td class="text-end">{{ Number(it.unit || 0).toLocaleString() }}</td>
                      <td class="text-end fw-bold">{{ Number(it.line || 0).toLocaleString() }}</td>
                    </tr>
                    <tr v-if="!billItems.length">
                      <td colspan="4" class="text-center text-muted py-4">
                        明細はありません
                      </td>
                    </tr>
                  </tbody>
                  <tfoot class="table-light">
                    <tr>
                      <th colspan="3" class="text-end">小計</th>
                      <th class="text-end">{{ totals.subtotal.toLocaleString() }}</th>
                    </tr>
                    <tr>
                      <th colspan="3" class="text-end">サービス料</th>
                      <th class="text-end">{{ totals.service.toLocaleString() }}</th>
                    </tr>
                    <tr>
                      <th colspan="3" class="text-end">税</th>
                      <th class="text-end">{{ totals.tax.toLocaleString() }}</th>
                    </tr>
                    <tr class="fw-bold">
                      <th colspan="3" class="text-end">合計</th>
                      <th class="text-end">{{ totals.grand_total.toLocaleString() }}</th>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </template>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="close">閉じる</button>
        </div>

      </div>
    </div>
  </div>
</template>
