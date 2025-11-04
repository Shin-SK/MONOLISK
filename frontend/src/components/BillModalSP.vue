<script setup>
import { computed, ref, toRef, watch, nextTick } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import BasicsPanel from '@/components/panel/BasicsPanel.vue'
import CastsPanelSP  from '@/components/spPanel/CastsPanelSP.vue'
import OrderPanelSP  from '@/components/spPanel/OrderPanelSP.vue'
import PayPanelSP    from '@/components/spPanel/PayPanelSP.vue'
import useBillEditor from '@/composables/useBillEditor'
import ProvisionalPanelSP from '@/components/spPanel/ProvisionalPanelSP.vue'
import { useRoles } from '@/composables/useRoles'
import {
  api, addBillItem, updateBillCustomers, updateBillTable, updateBillCasts,
  fetchBill, deleteBillItem, patchBillItemQty, fetchMasters,
  createBill, patchBill,
  setBillDiscountByCode, updateBillDiscountRule,
 } from '@/api'

const { hasRole } = useRoles()
const canProvisional = computed(() => hasRole(['manager','owner']))


const props = defineProps({
  modelValue: Boolean,
  bill: { type: Object, required: true },
  serviceRate: { type: Number, default: 0.3 },
  taxRate:    { type: Number, default: 0.1 },
})
const emit = defineEmits(['update:modelValue','saved','updated','closed'])

const visible = computed({
  get: () => props.modelValue,
  set: v  => emit('update:modelValue', v)
})
const pane = ref('base')

/* composable */
const ed = useBillEditor(toRef(props,'bill'))

/* 席種は親でローカル管理 */
const seatType = ref('main')
function onSeatTypeChange (v) {
  seatType.value = v || 'main'
}

watch(visible, v => {
  if (!v) return
  seatType.value = props.bill?.table?.seat_type || 'main'
})

/* テーブル配列から席種候補を自動生成 */
const seatTypeOptions = computed(() => {
  const tbls = ed.tables?.value || []
  const set = new Set(tbls.map(t => t?.seat_type || 'main'))
  if (!set.size) return [
    { code:'main', label:'メイン' },
    { code:'counter', label:'カウンター' },
    { code:'box', label:'ボックス' },
  ]
  const label = c => (c==='main' ? 'メイン' : c==='counter' ? 'カウンター' : c==='box' ? 'ボックス' : c)
  return Array.from(set).map(code => ({ code, label: label(code) }))
})

/* マスター解決（配列/結果オブジェクト/表記ゆれ吸収） */
const masterMap = ref({})
async function ensureMasters(){
  if (Object.keys(masterMap.value).length) return
  const prim = (ed.masters?.value && ed.masters.value.length) ? ed.masters.value : null
  const raw  = prim || await fetchMasters()
  const arr  = Array.isArray(raw) ? raw : (raw?.results ?? [])
  const dict = {}
  for (const m of arr) {
    const code = String(m?.code ?? '').trim()
    if (!code) continue
    for (const v of [code, code.toLowerCase(), code.replace(/[-_]/g,'').toLowerCase()]) dict[v] = m
  }
  masterMap.value = dict
  if (!Object.keys(dict).length) console.warn('[masters] empty; check X-Store-Id / endpoint')
}
const getMasterId = (code, ...alts) => {
  const map = masterMap.value
  const cand = [code, ...alts].filter(Boolean).map(s=>String(s))
  for (const k of cand) {
    for (const n of [k, k.toLowerCase(), k.replace(/[-_]/g,'').toLowerCase()]) {
      if (map[n]?.id) return map[n].id
    }
  }
  console.warn('[master not found candidates]', cand)
  return null
}

/* Bill 確保 → 行追加の順に統一 */
async function ensureBillId () {
  if (props.bill?.id) return props.bill.id
  const tableId = props.bill?.table?.id ?? props.bill?.table_id_hint ?? ed.tableId.value ?? null
  if (!tableId) { alert('テーブルが未選択です'); throw new Error('no table') }
  const b = await createBill({ table: tableId })
  props.bill.id = b.id
  return b.id
}

/* SETの適用（BasicsPanel → 親で行追加） */
async function onApplySet (payload){
  await ensureMasters()
  const billId = await ensureBillId()

  // SET（男女：setMale / setFemale）
  for (const ln of payload.lines.filter(l => l.type==='set')) {
    if (!ln.qty) continue
    const mid = getMasterId(
      ln.code,
      ln.code === 'setMale' ? 'setmale'   : 'setfemale',
      ln.code === 'setMale' ? 'set-male'  : 'set-female'
    )
    if (!mid) { console.warn('master not found:', ln.code); continue }
    await addBillItem(billId, { item_master: mid, qty: ln.qty })
  }

  // 深夜（addonNight：人数分）
  for (const ln of payload.lines.filter(l => l.type==='addon')) {
    if (!ln.qty) continue
    const mid = getMasterId(ln.code, 'addonnight', 'night')
    if (!mid) { console.warn('addon master not found:', ln.code); continue }
    await addBillItem(billId, { item_master: mid, qty: ln.qty })
  }

  // ★ 割引は DiscountRule に一本化（行は足さない）
  if (payload.discount_code) {
    await setBillDiscountByCode(billId, payload.discount_code)
  } else {
    await updateBillDiscountRule(billId, null)
  }

  const fresh = await fetchBill(billId).catch(()=>null)
  emit('updated', fresh || billId)
}

/* 既存 */
const onChooseCourse = async (opt) => {
  const res = await ed.chooseCourse(opt)
  if (res?.updated) emit('updated', props.bill.id)
}
const pageTitle = computed(() => ({ base:'基本', casts:'キャスト', order:'注文', prov:'仮会計', pay:'会計' }[pane.value] || ''))
const onDutyIds = computed(() => Array.from(ed.onDutySet?.value ?? []))
const masterNameMap = computed(() => {
  const list = ed.masters?.value || []; const map = {}
  for (const m of list) if (m && m.id != null) map[String(m.id)] = m.name
  return map
})
const masterPriceMap = computed(() => {
  const list = ed.masters?.value || []; const map = {}
  for (const m of list) if (m && m.id != null) map[String(m.id)] = m.price_regular ?? null
  return map
})
const servedByOptions = computed(() => {
  const out = [], seen = new Set(), cc = Array.isArray(ed.currentCasts.value) ? ed.currentCasts.value : []
  for (const c of cc) { const id = Number(c?.id); if (!Number.isFinite(id)||seen.has(id)) continue; out.push({ id, label: c.stage_name || `cast#${id}` }); seen.add(id) }
  const stays = Array.isArray(props.bill?.stays) ? props.bill.stays : []
  for (const s of stays) { if (!s || s.left_at) continue; const id = Number(s.cast?.id); if (!Number.isFinite(id)||seen.has(id)) continue; out.push({ id, label: s.cast.stage_name || `cast#${id}` }); seen.add(id) }
  return out
})
const servedByMap = computed(() => { const map = {}; for (const c of servedByOptions.value || []) map[String(c.id)] = c.label; return map })

/* Pay 周り（既存） */
const displayGrandTotal = computed(() => props.bill?.grand_total ?? 0)
const payCurrent = computed(() => {
  const items = Array.isArray(props.bill?.items) ? props.bill.items : []
  const priceOf = (id) => (ed.masters?.value || []).find(m => m.id === id)?.price_regular || 0
  const sub = items.reduce((s,it) => s + ((Number(it.qty)||0) * priceOf(it.item_master, it.price)), 0)
  const svc = Math.round(sub * (props.serviceRate || 0))
  const tax = Math.round((sub + svc) * (props.taxRate || 0))
  return { sub, svc, tax, total: sub + svc + tax }
})
const paidCashRef     = ref(props.bill?.paid_cash ?? 0)
const paidCardRef     = ref(props.bill?.paid_card ?? 0)
const settledTotalRef = ref(props.bill?.settled_total ?? (props.bill?.grand_total || 0))
const paidTotal   = computed(() => (Number(paidCashRef.value)||0) + (Number(paidCardRef.value)||0))
const targetTotal = computed(() => Number(settledTotalRef.value) || Number(displayGrandTotal.value) || 0)
const diff        = computed(() => paidTotal.value - targetTotal.value)
const overPay     = computed(() => Math.max(0, diff.value))
const canClose    = computed(() => targetTotal.value > 0 && paidTotal.value >= targetTotal.value)
const memoRef = ref(props.bill?.memo ?? '')
const payRef = ref(null)
watch(() => props.bill?.memo, v => { memoRef.value = v ?? '' })

watch(visible, v => {
  if (!v) return
  memoRef.value = props.bill?.memo ?? ''
})

const incItem = async (it) => {
  try{
    const newQty = (Number(it.qty)||0) + 1
    await patchBillItemQty(props.bill.id, it.id, newQty)
    it.qty = newQty
    it.subtotal = (masterPriceMap.value[String(it.item_master)] || 0) * newQty
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('updated', fresh || props.bill.id)
  }catch(e){ console.error(e); alert('数量を増やせませんでした') }
}
const decItem = async (it) => {
  try{
    const newQty = (Number(it.qty)||0) - 1
    if (newQty <= 0) {
      if (!confirm('削除しますか？')) return
      await deleteBillItem(props.bill.id, it.id)
    } else {
      await patchBillItemQty(props.bill.id, it.id, newQty)
      it.qty = newQty
      it.subtotal = (masterPriceMap.value[String(it.item_master)] || 0) * newQty
    }
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('updated', fresh || props.bill.id)
  }catch(e){ console.error(e); alert('数量を減らせませんでした') }
}
const removeItem = async (it) => {
  try{
    await deleteBillItem(props.bill.id, it.id)
    const fresh = await fetchBill(props.bill.id).catch(()=>null)
    emit('updated', fresh || props.bill.id)
  }catch(e){ console.error(e); alert('削除に失敗しました') }
}

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
    await nextTick()
    const billId   = props.bill.id
    const memoStr  = (payRef.value?.getMemo?.() ?? '').toString()
    const settled  = Number(settledTotalRef.value) || Number(displayGrandTotal.value) || 0
    const paidCash = Number(paidCashRef.value) || 0
    const paidCard = Number(paidCardRef.value) || 0

    // ① 楽観反映（UI即更新）
    props.bill.paid_cash     = paidCash
    props.bill.paid_card     = paidCard
    props.bill.settled_total = settled
    props.bill.memo          = memoStr
    props.bill.closed_at     = new Date().toISOString()   // “閉店”を即時表示
    // 可能ならリスト側も同期
    try{
      const { useBills } = await import('@/stores/useBills')
      const bs = useBills()
      const i = bs.list.findIndex(b => Number(b.id) === Number(billId))
      if (i >= 0) {
        bs.list[i] = { ...bs.list[i],
          paid_cash: paidCash, paid_card: paidCard, settled_total: settled,
          memo: memoStr, closed_at: props.bill.closed_at
        }
      }
    }catch{}

    // ② 裏送信（順序安全：patch → close → reconcile）
    enqueue('patchBill', { id: billId, payload: {
      paid_cash: paidCash, paid_card: paidCard, memo: memoStr,
    }})
    enqueue('closeBill', { id: billId, payload: { settled_total: settled }})
    enqueue('reconcile', { id: billId })

    // ③ 親へ通知（UIはもう閉店表示。ここでモーダルも閉じる）
    emit('saved', { id: billId })
    visible.value = false
  }catch(e){
    console.error(e)
    alert('会計に失敗しました（オフラインでも後で確定されます）')
  }finally{
    closing.value = false
  }
}


/* 保存（既存） */
const saving = ref(false)
async function handleSave(){
  if (saving.value) return
  saving.value = true
  try{
    const optimistic = await ed.save()
    emit('saved', optimistic)   // 親はこのイベントでカード即時反映済み
  }finally{
    saving.value = false
  }
}
</script>

<template>
  <BaseModal v-if="bill" v-model="visible" class="billmodal-sp">
    <template #header>
      <div id="header" class="header-bar">
        <div class="page-title">{{ pageTitle }}</div>
        <div class="button-area fs-5">
          <button :disabled="saving" @click="handleSave" aria-label="save"><IconDeviceFloppy /></button>
          <button @click="$emit('update:modelValue', false)" aria-label="close"><IconX /></button>
        </div>
      </div>
    </template>

    <BasicsPanel
      v-show="pane==='base'"
      :tables="ed.tables.value || []"
      :table-id="ed.tableId.value"
      :pax="ed.pax.value"
      :course-options="ed.courseOptions.value || []"
      :seat-type-options="seatTypeOptions"
      :seat-type="seatType"
      :show-customer="true"
      :customer-name="ed.customerName.value"
      :customer-results="ed.custResults.value"
      :customer-searching="ed.custLoading.value"
      @update:seatType="onSeatTypeChange" 
      @update:tableId="v => (ed.tableId.value = v)"
      @update:pax="v => (ed.pax.value = v)"
      @chooseCourse="(opt, qty) => onChooseCourse(opt, qty)"
      @clearCustomer="ed.clearCustomer"
      @searchCustomer="ed.searchCustomers"
      @pickCustomer="ed.pickCustomerInline"
      @applySet="onApplySet"
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
      @setDohan="ed.setDohan"
      @setMain="ed.setMain"
      @removeCast="ed.removeCast"
      @save="handleSave"
    />

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
      ref="payRef"
      :items="bill.items || []"
      :master-name-map="masterNameMap"
      :served-by-map="servedByMap"
      :bill-opened-at="bill.opened_at || ''"
      :current="payCurrent"
      :display-grand-total="displayGrandTotal"
      :memo="props.bill?.memo || ''"
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

    <ProvisionalPanelSP
      v-show="pane==='prov' && canProvisional"
      :key="`prov-${props.bill?.id || 'new'}`"
      :bill="props.bill || {}"
      :ed="ed"
      :service-rate="props.serviceRate"
      :tax-rate="props.taxRate"
    />

    <template #footer>
      <div class="modal-footer p-0" style="border-top:1px #f5f5f5 solid;">
        <div class="w-100 px-2 py-2 pb-safe bg-white">
          <div class="nav nav-pills nav-fill small gap-2 pills-flat">
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='base'}"  @click="pane='base'"><IconFileNeutral /><span>基本</span></button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='casts'}" @click="pane='casts'"><IconUser /><span>キャスト</span></button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='order'}" @click="pane='order'"><IconShoppingCart /><span>注文</span></button>
            <button v-if="canProvisional" type="button" class="nav-link d-flex flex-column" :class="{active: pane==='prov'}" @click="pane='prov'"><IconCalculator /><span>仮</span></button>
            <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='pay'}"   @click="pane='pay'"><IconReceiptYen /><span>会計</span></button>
          </div>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped lang="scss">
.pills-flat{
  --bs-nav-pills-link-active-bg: white;
  --bs-nav-pills-link-active-color: #000;
}
.pills-flat .nav-link{ background-color:white; color:#a9a9a9; border-radius:.75rem; }
.pills-flat .nav-link.active{ color:#000; font-weight:700; }
.nav{
 flex-wrap: nowrap;
 button{
  white-space: nowrap;
 }
}
</style>
