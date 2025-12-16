<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import dayjs from 'dayjs'
import { fetchBill, fetchCustomer, fetchBillItemsByBillId, updateCustomer } from '@/api'
import CustomerPicker from './CustomerPicker.vue'

const props = defineProps({
  billId: { type: Number, default: null },
  show:   { type: Boolean, default: false },
  // 親から渡される統計（任意）: { name, visit_count, last_visit_at }
  customerStats: { type: Object, default: null },
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
const editCustomerId = ref(null)

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

// Bill から主顧客IDを優先度付きで決定する
function pickPrimaryCustomerIdFromBill(b) {
  if (!b) return null

  // 1) 明示があれば最優先
  if (b.customer_id) return b.customer_id
  if (b.customer?.id) return b.customer.id

  const list = Array.isArray(b.customers) ? b.customers : []
  if (!list.length) return null

  const disp = (b.customer_display_name || '').trim()

  // 2) customer_display_name と alias / full_name が一致するものを優先
  if (disp) {
    const hit = list.find(c =>
      (c.alias && c.alias.trim() === disp) ||
      (c.full_name && c.full_name.trim() === disp)
    )
    if (hit?.id != null) return hit.id
  }

  // 3) 「空っぽじゃない顧客」を優先（最低限の実用ルール）
  const nonEmpty = list.find(c =>
    (c.full_name && c.full_name.trim()) ||
    (c.alias && c.alias.trim()) ||
    (c.phone && c.phone.trim())
  )
  if (nonEmpty?.id != null) return nonEmpty.id

  // 4) 最後の手段
  return list[0]?.id ?? null
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

    // 顧客詳細：pickPrimaryCustomerIdFromBill で主顧客を決定
    const cid = pickPrimaryCustomerIdFromBill(b)
    if (cid) {
      try {
        customer.value = await fetchCustomer(cid)
      } catch (e) {
        console.warn('顧客情報の取得に失敗しました (404かアクセス権なし)', e)
        // customer.value は null のまま（顧客情報なしで続行）
      }
    }

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
    // 編集モード突入時点でIDも同期（CustomerPicker 初期化用）
    const cid = customer.value?.id || pickPrimaryCustomerIdFromBill(bill.value)
    editCustomerId.value = cid ?? null
  }
})

function close () { 
  isEditing.value = false
  emit('close') 
}
function setTab(t){ activeTab.value = t }

function startEdit() {
  console.log('startEdit called', customer.value)
  // pickPrimaryCustomerIdFromBill で一貫して顧客IDを決定
  const customerId = customer.value?.id || pickPrimaryCustomerIdFromBill(bill.value)
  if (!customerId) {
    console.warn('startEdit: customerId not found from bill')
    return
  }
  editCustomerId.value = customerId
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

function onPicked(obj){
  // ピック時はローカル表示を更新（保存はしない）
  if (obj?.id != null) {
    editCustomerId.value = obj.id
  }
}

function onSaved(saved){
  // CustomerPicker 側で保存完了したらモーダルの表示も更新して閉じる
  if (saved && saved.id != null) {
    customer.value = saved
  }
  isEditing.value = false
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
            <div v-if="activeTab==='customer'"
            class="mt-4">
              <div v-if="!isEditing">
                <dl class="row mb-0 g-2">
                  <dt class="col-3">来店日時</dt>
                  <dd class="col-9">{{ openedAt }}</dd>

                  <dt class="col-3">顧客名</dt>
                  <dd class="col-9">{{ customer?.full_name || customer?.display_name || bill?.customer_display_name || '—' }}</dd>

                  <dt class="col-3">電話</dt>
                  <dd class="col-9">{{ customer?.phone || '—' }}</dd>

                  <dt class="col-3">ボトル</dt>
                  <dd class="col-9">
                    <div v-if="customer?.has_bottle" class="d-flex align-items-center gap-2">
                      <div class="df-center">
                        <span class="badge bg-light text-dark">棚番号</span>
                        <span class="ms-2">{{ customer?.bottle_shelf || '—' }}</span>
                      </div>
                      <div class="df-center">
                        <span class="badge bg-light text-dark">種類</span>
                        <span class="ms-2">{{ customer?.bottle_memo || '—' }}</span>
                      </div>
                    </div>
                    <div v-else class="df-center">
                      なし
                    </div>
                  </dd>

                  <dt class="col-3">メモ</dt>
                  <dd class="col-9">
                    <pre class="mb-0" style="white-space:pre-wrap">{{ customer?.memo || '—' }}</pre>
                  </dd>
                  

                  <dt class="col-3">来店回数</dt>
                  <dd class="col-9">{{ (props.customerStats?.visit_count ?? customer?.visit_count) ?? '—' }}</dd>

                  <dt class="col-3">直近来店</dt>
                  <dd class="col-9">
                    <span v-if="props.customerStats?.last_visit_at || customer?.last_visit_at">
                      {{ dayjs(props.customerStats?.last_visit_at || customer?.last_visit_at).format('YYYY/MM/DD') }}
                    </span>
                    <span v-else>—</span>
                  </dd>
                </dl>
                <button type="button" class="btn btn-primary btn-sm mt-4" @click="startEdit">編集</button>
              </div>

              <!-- ＊上の編集を押すと、下のCustomerPickerが出るようにしたんだけど、情報が引き継がれない -->

              <div v-else>
                <!-- CustomerPicker で顧客情報の編集を行う -->
                <CustomerPicker
                  v-if="editCustomerId != null"
                  v-model="editCustomerId"
                  :key="editCustomerId || 'new'"
                  @picked="onPicked"
                  @saved="onSaved"
                />
                <div v-else class="text-muted">読み込み中…</div>
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
      </div>
    </div>
  </div>
</template>
