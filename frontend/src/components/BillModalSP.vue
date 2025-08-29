<script setup>
import { computed, ref, toRef, watch } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import BasicsPanelSP from '@/components/BasicsPanelSP.vue'
import CastsPanelSP  from '@/components/CastsPanelSP.vue'
import useBillEditor from '@/composables/useBillEditor'
import OrderPanelSP  from '@/components/OrderPanelSP.vue'
import PayPanelSP    from '@/components/PayPanelSP.vue'
/* ▼ 保存に必要なAPI */
import { api, addBillItem, updateBillCustomers, updateBillTable, updateBillCasts, fetchBill, deleteBillItem } from '@/api'


const props = defineProps({
  modelValue: Boolean,
  bill: Object,
  serviceRate: { type: Number, default: 0.3 },
  taxRate:    { type: Number, default: 0.1 },
})
const emit = defineEmits(['update:modelValue','saved','updated','closed'])

const visible = computed({
  get: () => props.modelValue,
  set: v  => emit('update:modelValue', v)
})
const pane = ref('base')

/* composable（Basics / Casts） */
const ed = useBillEditor(toRef(props, 'bill'))

/* 開いた瞬間の初期化 */
watch(visible, v => {
  if (!v) return
  pane.value = 'base'
  if (ed.showCustModal?.value) ed.showCustModal.value = false
  if (ed.activeCustId?.value)  ed.activeCustId.value  = null
})

/* セット追加の“既存時のみupdated通知” */
const onChooseCourse = async (opt) => {
  const res = await ed.chooseCourse(opt)
  if (res?.updated) emit('updated', props.bill.id)
}

/* ヘッダーのタイトル（pane→表示名） */
const pageTitle = computed(() => ({ base:'基本', casts:'キャスト', order:'注文', pay:'会計' }[pane.value] || ''))

/* 出勤配列 */
const onDutyIds = computed(() => Array.from(ed.onDutySet?.value ?? []))

// 提供者セレクト用（現在ついているキャスト）
const servedByOptions = computed(() => {
  const out = []
  const seen = new Set()
  const cc = Array.isArray(ed.currentCasts.value) ? ed.currentCasts.value : []
  for (const c of cc) {
    const id = Number(c?.id)
    if (!Number.isFinite(id) || seen.has(id)) continue
    out.push({ id, label: c.stage_name || `cast#${id}` })
    seen.add(id)
  }
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  for (const s of stays) {
    if (!s || s.left_at) continue
    const id = Number(s.cast?.id)
    if (!Number.isFinite(id) || seen.has(id)) continue
    out.push({ id, label: s.cast.stage_name || `cast#${id}` })
    seen.add(id)
  }
  return out
})

//  品目名マップ（id→name）
const masterNameMap = computed(() => {
  const list = ed.masters?.value || []
  const map = {}
  for (const m of list) if (m && m.id != null) map[String(m.id)] = m.name
  return map
})

const masterPriceMap = computed(() => {
  const list = ed.masters?.value || []
  const map = {}
  for (const m of list) if (m && m.id != null) map[String(m.id)] = m.price_regular ?? null
  return map
})

// 提供者名マップ（id→label）— 上の options に追従
const servedByMap = computed(() => {
  const map = {}
  for (const c of servedByOptions.value || []) map[String(c.id)] = c.label
  return map
})

/* ===== Pay（PC相当の計算をSPに） ===== */
const displayGrandTotal = computed(() => props.bill?.grand_total ?? 0)

// 現状確定分（PCの current と同じ）
const payCurrent = computed(() => {
  const items = Array.isArray(props.bill?.items) ? props.bill.items : []
  const masters = ed.masters?.value || []
  const priceOf = (id) => masters.find(m => m.id === id)?.price_regular || 0
  const sub = items.reduce((s,it) => s + (Number(it.qty)||0) * (priceOf(it.item_master) || it.price || 0), 0)
  const svc = Math.round(sub * (props.serviceRate || 0))
  const tax = Math.round((sub + svc) * (props.taxRate || 0))
  return { sub, svc, tax, total: sub + svc + tax }
})

// 入力状態（初期値はBillから）
const paidCashRef     = ref(props.bill?.paid_cash ?? 0)
const paidCardRef     = ref(props.bill?.paid_card ?? 0)
const settledTotalRef = ref(props.bill?.settled_total ?? (props.bill?.grand_total || 0))

const paidTotal   = computed(() => (Number(paidCashRef.value)||0) + (Number(paidCardRef.value)||0))
const targetTotal = computed(() => Number(settledTotalRef.value) || Number(displayGrandTotal.value) || 0)
const diff        = computed(() => paidTotal.value - targetTotal.value)
const overPay     = computed(() => Math.max(0, diff.value))
const canClose    = computed(() => targetTotal.value > 0 && paidTotal.value >= targetTotal.value)

// 履歴編集（±/削除）
const incItem = async (it) => {
  try{
    await api.patch(`billing/bill-items/${it.id}/`, { qty: Number(it.qty||0)+1 })
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('updated', fresh || props.bill.id)   // ★ saved→updated
  }catch(e){ console.error(e); alert('数量を増やせませんでした') }
}

const decItem = async (it) => {
  try{
    const newQty = Number(it.qty||0) - 1
    if (newQty <= 0) {
      if (!confirm('削除しますか？')) return
      await deleteBillItem(props.bill.id, it.id)
    } else {
      await api.patch(`billing/bill-items/${it.id}/`, { qty: newQty })
    }
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('updated', fresh || props.bill.id)   // ★ saved→updated
  }catch(e){ console.error(e); alert('数量を減らせませんでした') }
}

const removeItem = async (it) => {
  try{
    await deleteBillItem(props.bill.id, it.id)
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('updated', fresh || props.bill.id)   // ★ saved→updated
  }catch(e){ console.error(e); alert('削除に失敗しました') }
}

// update受け取り用の関数（テンプレ内で .value を触らない）
const setSettledTotal = (v) => { settledTotalRef.value = Number(v) || 0 }
const setPaidCash     = (v) => { paidCashRef.value     = Number(v) || 0 }
const setPaidCard     = (v) => { paidCardRef.value     = Number(v) || 0 }

function useGrandTotal(){ settledTotalRef.value = Number(displayGrandTotal.value) || 0 }
function fillRemainderToCard(){
  const need = Math.max(0, targetTotal.value - (Number(paidCashRef.value)||0))
  paidCardRef.value = need
}

const closing = ref(false)
async function confirmClose(){
  if (closing.value || !props.bill?.id) return
  closing.value = true
  try{
    await api.patch(`billing/bills/${props.bill.id}/`, {
      paid_cash: Number(paidCashRef.value)||0,
      paid_card: Number(paidCardRef.value)||0,
    })
    await api.post(`billing/bills/${props.bill.id}/close/`, {
      settled_total: Number(settledTotalRef.value)||Number(displayGrandTotal.value)||0,
    })
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('saved', fresh || props.bill.id)
    visible.value = false
  }catch(e){ console.error(e); alert('会計に失敗しました') }
  finally{ closing.value = false }
}

/* ▼ 保存ボタン */
const saving = ref(false)
const handleSave = async () => {
  if (saving.value) return
  saving.value = true
  try{
    let billId = props.bill?.id || null

    /* 1) 新規なら伝票作成＋顧客反映 */
    if (!ed.isNew.value) {
      // 既存：卓変更だけ反映（必要なら）
      const currentTableId = props.bill.table?.id ?? props.bill.table ?? null
      if (ed.tableId.value !== currentTableId) {
        await updateBillTable(props.bill.id, ed.tableId.value)
      }
      billId = props.bill.id
    } else {
      const { data: created } = await api.post('billing/bills/', {
        table_id: ed.tableId.value ?? null,
        // NOT NULL対策：現在時刻を必ず入れる（ISO）
        opened_at: new Date().toISOString(),
        expected_out: null,
      })
      billId = created.id
      // 顧客（選択済みなら反映）
      if ((props.bill.customers?.length ?? 0) > 0) {
        await updateBillCustomers(billId, props.bill.customers)
      }
      // キャスト（選択済みなら反映）
      if (ed.mainIds.value.length || ed.inhouseIds.value.length || ed.freeIds.value.length) {
        await updateBillCasts(billId, {
          nomIds:  [...ed.mainIds.value],
          inIds:   [...ed.inhouseIds.value],
          freeIds: [...ed.freeIds.value],
        })
      }
    }

    /* 2) pending の注文を確定 */
    for (const it of ed.pending.value) {
      await addBillItem(billId, {
        item_master: it.master_id,
        qty: it.qty,
        served_by_cast_id: it.cast_id ?? undefined,
      })
    }
    ed.pending.value = []

    /* 3) 最新を取り直して親へ渡す */
    const fresh = await fetchBill(billId).catch(() => null)
    emit('saved', fresh || billId)
  }catch(e){
    console.error(e); alert('保存に失敗しました')
  }finally{
    saving.value = false
  }
}
</script>

<template>
  <BaseModal v-if="bill" v-model="visible" class="billmodal-sp">
    <!-- ▼ ヘッダー（左：ページタイトル／右：保存＆閉じる） -->
    <template #header>
      <div id="header" class="header-bar">
        <div class="page-title">{{ pageTitle }}</div>
        <div class="button-area">
          <button :disabled="saving" @click="handleSave" aria-label="save">
            <IconDeviceFloppy />
          </button>
          <button @click="$emit('update:modelValue', false)" aria-label="close">
            <IconX />
          </button>
        </div>
      </div>
    </template>

    <!-- 本文 -->
    <BasicsPanelSP
      v-show="pane==='base'"
      :tables="ed.tables.value || []"
      :table-id="ed.tableId.value"
      :pax="ed.pax.value"
      :course-options="ed.courseOptions.value || []"
      :customer-name="ed.customerName.value"
      :customer-results="ed.custResults.value"
      :customer-searching="ed.custLoading.value"
      @update:tableId="v => (ed.tableId.value = v)"
      @update:pax="v => (ed.pax.value = v)"
      @chooseCourse="onChooseCourse"
      @clearCustomer="ed.clearCustomer"
      @searchCustomer="ed.searchCustomers"
      @pickCustomer="ed.pickCustomerInline"
      @save="handleSave"
    />

    <CastsPanelSP
      v-show="pane==='casts'"
      :current-casts="ed.currentCasts.value"
      :bench-casts="ed.benchCasts.value"
      :on-duty-ids="onDutyIds"
      :keyword="ed.castKeyword.value"
      @update:keyword="v => (ed.castKeyword.value = v)"
      @setFree="ed.setFree"
      @setInhouse="ed.setInhouse"
      @setMain="ed.setMain"
      @removeCast="ed.removeCast"
      @save="handleSave"
    />

    <!-- ここをコピペで差し替え -->
    <OrderPanelSP
      v-show="pane==='order'"
      :cat-options="ed.orderCatOptions.value || []"
      :selected-cat="ed.selectedOrderCat.value"
      :order-masters="ed.orderMasters.value || []"
      :served-by-options="servedByOptions"
      v-model:served-by-cast-id="ed.servedByCastId.value"
      :pending="ed.pending.value"
      :master-name-map="masterNameMap"
      :served-by-map="servedByMap"
      :master-price-map="masterPriceMap"
      @update:selectedCat="v => (ed.selectedOrderCat.value = v)"
      @addPending="(id, qty) => ed.addPending(id, qty)"
      @removePending="i => ed.pending.value.splice(i,1)"
      @clearPending="() => (ed.pending.value = [])"
      @placeOrder="handleSave"
    />

    <PayPanelSP
      v-show="pane==='pay'"
      :items="bill.items || []"
      :master-name-map="masterNameMap"
      :served-by-map="servedByMap"
      :bill-opened-at="bill.opened_at || ''"
      :current="payCurrent"
      :display-grand-total="displayGrandTotal"

      :settled-total="settledTotalRef"
      :paid-cash="paidCashRef"
      :paid-card="paidCardRef"

      :diff="diff"
      :over-pay="overPay"
      :can-close="canClose"

      @update:settledTotal="setSettledTotal"
      @update:paidCash="setPaidCash"
      @update:paidCard="setPaidCard"

      @useGrandTotal="useGrandTotal"
      @fillRemainderToCard="fillRemainderToCard"
      @confirmClose="confirmClose"
      @incItem="incItem"
      @decItem="decItem"
      @deleteItem="removeItem"
    />

    <!-- フッター（既存のまま） -->
    <template #footer>
      <div class="modal-footer p-0" style="border-top: 1px #f5f5f5 solid ;">
        <div class="w-100 px-2 py-2 pb-safe bg-white">
          <div class="nav nav-pills nav-fill small gap-2 pills-flat">
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='base'}"  @click="pane='base'">
              <IconFileNeutral />
              <span>基本</span>
            </button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='casts'}" @click="pane='casts'">
              <IconUser />
              <span>キャスト</span>
            </button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='order'}" @click="pane='order'">
              <IconShoppingCart />
              <span>注文</span>
            </button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='pay'}"   @click="pane='pay'">
              <IconReceiptYen />
              <span>会計</span>
            </button>
          </div>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
/* アクティブ時の反転色を変数で上書き（黒文字・薄グレー背景） */
.pills-flat{
  --bs-nav-pills-link-active-bg: white;
  --bs-nav-pills-link-active-color: #000;
}

/* 常時：薄いグレー＆やや薄い文字色 */
.pills-flat .nav-link{
  background-color: white;
  color: #a9a9a9;
  border-radius: .75rem;
}

/* アクティブ：黒＋太字（背景は常時と同じ薄グレー） */
.pills-flat .nav-link.active{
  color: #000;
  font-weight: 700; /* = fw-bold */
}

/* もし他CSSに負ける場合の保険（必要時だけ） */
/*
.pills-flat .nav-link.active{
  background-color: var(--bs-gray-100) !important;
  color: #000 !important;
}
*/
</style>