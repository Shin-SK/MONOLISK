<!-- src/views/cast/Order.vue -->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUser } from '@/stores/useUser'
import useBillEditor from '@/composables/useBillEditor'
import OrderPanelSP from '@/components/spPanel/OrderPanelSP.vue'
import PayPanelSP   from '@/components/spPanel/PayPanelSP.vue'
import ProvisionalPanelSP from '@/components/spPanel/ProvisionalPanelSP.vue'
import { api, fetchBills, fetchBill, addBillItem, deleteBillItem, patchBillItemQty } from '@/api'
import dayjs from 'dayjs'


const route  = useRoute()
const router = useRouter()
const user   = useUser()

/* 疑似フッター用 */
const pane = ref('order')

/* ---- Bill 選択（本指名＆在席の“自分の卓”） ---- */
const ready        = ref(false)
const candidates   = ref([])          // [{ id, tableName }]
const targetBillId = ref(null)
const currentBill  = ref(null)
const hasTarget    = computed(() => !!targetBillId.value)

async function resolveMyTargets(){
  if (!user.me) await user.fetchMe?.()
  const meCastId = user.me?.cast_id
  const data  = await fetchBills({ limit: 200 })
  const bills = Array.isArray(data.results) ? data.results : data
  const hits  = []
  for (const b of bills) {
    const stays = b.stays || []
    const ok = stays.some(s =>
      s.cast?.id === meCastId && s.is_honshimei === true && !s.left_at
    )
    if (ok) hits.push({ id: b.id, tableName: b.table?.name || `#${b.table?.id || '-'}` })
  }
  candidates.value = hits
  const q = Number(route.query.bill || 0) || null
  if (q && hits.some(h => h.id === q)) await pickBill(q)
  else if (hits.length === 1)          await pickBill(hits[0].id)
}

function storeIdOfBill(b){
  const t = b?.table
  return t?.store ?? t?.store_id ?? null
}
function ensureStoreHeaderFor(b){
  const sid = storeIdOfBill(b)
  if (!sid) return
  const cur = localStorage.getItem('store_id')
  if (String(cur) !== String(sid)) localStorage.setItem('store_id', String(sid))
}

async function pickBill(bid){
  targetBillId.value = bid
  currentBill.value  = await fetchBill(bid).catch(()=>null)
  // ed にも反映
  edBill.value = currentBill.value || edBill.value
  ensureStoreHeaderFor(currentBill.value)
}

/* ---- useBillEditor を“親”として利用（カテゴリ生成/絞り込みは ed に委譲） ---- */

const guessStoreId = computed(() => {
  const fromMe = user.me?.current_store_id
  if (fromMe != null) return fromMe
  const s = localStorage.getItem('store_id')
  const n = Number(s)
  return Number.isFinite(n) ? n : null
})

/* ed 用の Bill 参照（最初は推測 store で起動 → pickBill 後に差し替え） */
const edBill = ref({
  id: null,
  table: { store: guessStoreId.value },
  customers: [],
  stays: [],
})
watch(guessStoreId, v => {
  if (!currentBill.value && v) edBill.value = { ...edBill.value, table:{ store:v } }
})

const ed = useBillEditor(edBill)

const catOptionsArr       = computed(() => ed.orderCatOptions?.value || [])
const orderMastersArr     = computed(() => ed.orderMasters?.value || [])
const selectedCatVal      = computed({
  get: () => ed.selectedOrderCat?.value ?? null,
  set: v  => { ed.selectedOrderCat.value = v }
})
const servedByOptionsArr  = computed(() => servedByOptions.value || [])
const servedByCastIdModel = computed({
  get: () => ed.servedByCastId?.value ?? null,
  set: v  => { ed.servedByCastId.value = v }
})
const pendingArr          = computed(() => pending.value || [])


// ヘッダーの情報
const tableLabel = computed(() => {
  const t = currentBill.value?.table
  const id = typeof t === 'object' ? t?.id : t
  const nameFromObj = typeof t === 'object' ? (t?.name || null) : null
  if (nameFromObj) return nameFromObj
  const found = (ed.tables?.value || []).find(tb => tb && tb.id === id)
  return found?.name || (id ? `${id}` : '-')
})

const peopleCount = computed(() => {
  const pax = Number(currentBill.value?.pax)
  if (Number.isFinite(pax) && pax > 0) return pax
  const custs = currentBill.value?.customers
  return Array.isArray(custs) ? custs.length : null
})

const openedAt = computed(() =>
  currentBill.value?.opened_at ? dayjs(currentBill.value.opened_at).format('HH:mm') : null
)
const endedAt  = computed(() => {
  const end = currentBill.value?.closed_at || currentBill.value?.expected_out || null
  return end ? dayjs(end).format('HH:mm') : null
})



/* ---- 提供者（未指定＋在席キャスト＋自分） ---- */
const servedByOptions = computed(() => {
  const seen = new Set()
  const out  = [{ id:null, label:'未指定' }]
  const stays = currentBill.value?.stays || []
  for (const s of stays) {
    if (!s || s.left_at || !s.cast?.id) continue
    const id = Number(s.cast.id)
    if (seen.has(id)) continue
    out.push({ id, label: s.cast.stage_name || `cast#${id}` })
    seen.add(id)
  }
  const meId = user.me?.cast_id
  if (meId && !seen.has(meId)) out.push({ id: meId, label: user.me?.display_name || '自分' })
  return out
})

/* ---- カート＆発注（edの pending / servedByCastId を利用） ---- */
const pending          = ed.pending              // ref
const servedByCastId   = ed.servedByCastId       // ref
function addPending(masterId, qty){ ed.addPending(masterId, qty) }
function removePending(i){ pending.value.splice(i,1) }
function clearPending(){ pending.value = [] }

const masterNameMap  = computed(() => {
  const map = {}
  for (const m of (ed.masters?.value || [])) map[String(m.id)] = m.name
  return map
})
const masterPriceMap = computed(() => {
  const map = {}
  for (const m of (ed.masters?.value || [])) map[String(m.id)] = m.price_regular ?? null
  return map
})
const servedByMap = computed(() => {
  const map = {}
  for (const o of servedByOptions.value) map[String(o.id)] = o.label
  return map
})

async function placeOrder(){
  if (!targetBillId.value) return alert('卓が未選択です')
  if (!pending.value.length) return
  try{
    // ★ 念押しで毎回同期（store切替直後でも安全）
    ensureStoreHeaderFor(currentBill.value)
    // 権限チェック（念のためクライアント側でも早期警告）
    const hasCap = (user.me?.claims || []).includes('cast_order_self')
    if (!hasCap) { alert('権限がありません（cast_order_self）'); return }

    for (const p of pending.value) {
      await addBillItem(targetBillId.value, {
        item_master: p.master_id,
        qty: p.qty,
        served_by_cast_id: p.cast_id ?? undefined,
      })
    }
    pending.value = []
    alert('送信しました')
  }catch(e){
    const msg = e?.response?.data?.detail || JSON.stringify(e?.response?.data || {}, null, 2)
    console.error(e);
    alert(`注文に失敗しました / ${msg}`)
  }
}


/* ==== ▼▼ 会計（PayPanelSP用） ▼▼ ================================== */
const SERVICE_RATE = 0.3
const TAX_RATE     = 0.1

// Billの金額系
const displayGrandTotal = computed(() => Number(currentBill.value?.grand_total) || 0)

// 現状確定分（本家と同じ式で再計）
const payCurrent = computed(() => {
  const items = Array.isArray(currentBill.value?.items) ? currentBill.value.items : []
  const priceOf = (id, fallback) => {
    const m = (ed.masters?.value || []).find(x => x && x.id === id)
    return Number(m?.price_regular ?? fallback ?? 0)
  }
  const sub = items.reduce((s, it) => s + (Number(it.qty)||0) * priceOf(it.item_master, it.price), 0)
  const svc = Math.round(sub * SERVICE_RATE)
  const tax = Math.round((sub + svc) * TAX_RATE)
  return { sub, svc, tax, total: sub + svc + tax }
})

// 入力状態（Bill変化で同期）
const paidCashRef     = ref(0)
const paidCardRef     = ref(0)
const settledTotalRef = ref(0)
watch(currentBill, (b) => {
  paidCashRef.value     = Number(b?.paid_cash ?? 0)
  paidCardRef.value     = Number(b?.paid_card ?? 0)
  settledTotalRef.value = Number(b?.settled_total ?? b?.grand_total ?? 0)
}, { immediate: true })

const paidTotal   = computed(() => (Number(paidCashRef.value)||0) + (Number(paidCardRef.value)||0))
const targetTotal = computed(() => Number(settledTotalRef.value) || Number(displayGrandTotal.value) || 0)
const diff        = computed(() => paidTotal.value - targetTotal.value)
const overPay     = computed(() => Math.max(0, diff.value))
const canClose    = computed(() => targetTotal.value > 0 && paidTotal.value >= targetTotal.value)

// 数量編集・削除（履歴リスト用）
const refreshBill = async () => { if (targetBillId.value) currentBill.value = await fetchBill(targetBillId.value).catch(()=>currentBill.value) }

const incItem = async (it) => {
  try{
    const newQty = (Number(it.qty)||0) + 1
    await patchBillItemQty(targetBillId.value, it.id, newQty)
    await refreshBill()
  }catch(e){ console.error(e); alert('数量を増やせませんでした') }
}

const decItem = async (it) => {
  try{
    const newQty = (Number(it.qty)||0) - 1
    if (newQty <= 0) {
      if (!confirm('削除しますか？')) return
      await deleteBillItem(targetBillId.value, it.id)
    } else {
      await patchBillItemQty(targetBillId.value, it.id, newQty)
    }
    await refreshBill()
  }catch(e){ console.error(e); alert('数量を減らせませんでした') }
}

const removeItem = async (it) => {
  try{
    await deleteBillItem(targetBillId.value, it.id)
    await refreshBill()
  }catch(e){ console.error(e); alert('削除に失敗しました') }
}

// 入力値バインド用
const setSettledTotal = (v) => { settledTotalRef.value = Number(v) || 0 }
const setPaidCash     = (v) => { paidCashRef.value     = Number(v) || 0 }
const setPaidCard     = (v) => { paidCardRef.value     = Number(v) || 0 }

function useGrandTotal(){ settledTotalRef.value = Number(displayGrandTotal.value) || 0 }
function fillRemainderToCard(){
  const need = Math.max(0, (Number(settledTotalRef.value)||0) - (Number(paidCashRef.value)||0))
  paidCardRef.value = need
}

const closing = ref(false)
async function confirmClose(){
  if (closing.value || !targetBillId.value) return
  closing.value = true
  try{
    // 念のためStoreヘッダ同期
    ensureStoreHeaderFor(currentBill.value)

    await api.patch(`billing/bills/${targetBillId.value}/`, {
      paid_cash: Number(paidCashRef.value)||0,
      paid_card: Number(paidCardRef.value)||0,
    })
    await api.post(`billing/bills/${targetBillId.value}/close/`, {
      settled_total: Number(settledTotalRef.value)||Number(displayGrandTotal.value)||0,
    })
    await refreshBill()
    alert('会計を確定しました')
    window.dispatchEvent(new CustomEvent('bill:closed'))
    router.replace('/cast/mypage')
  }catch(e){ console.error(e); alert('会計に失敗しました') }
  finally{ closing.value = false }
}
/* ==== ▲▲ 会計（PayPanelSP用） ▲▲ ================================== */



onMounted(async () => {
  await resolveMyTargets()
  ready.value = true
})

</script>

<template>
  <div class="py-3 cast-order-page">
    <div v-if="!ready">読み込み中…</div>

    <template v-else>
      <!-- 候補が複数：卓選択ゲート -->
      <div v-if="!hasTarget">
        <div v-if="candidates.length===0" class="alert alert-info">
          本指名で在席中の卓がありません。
        </div>
        <div v-else class="row g-2">
          <div class="col-6" v-for="c in candidates" :key="c.id">
            <button class="btn btn-outline-primary w-100" @click="pickBill(c.id)">
              卓 {{ c.tableName }} を選択
            </button>
          </div>
        </div>
      </div>

      <!-- 対象Bill決定後：本家（staff）と同じ挙動＝edの値をそのまま渡す -->
      <div v-else class="billmodal-sp">
        <div class="mb-3">
          <div class="wrap d-flex align-items-center gap-3 mb-3 fs-5">
            <span class="badge bg-secondary d-flex align-items-center gap-2">
              <IconNote size="16" />{{ targetBillId }}
            </span>
            <span class="badge bg-secondary d-flex align-items-center gap-2">
              <IconUsers size="16" /> {{ peopleCount != null ? peopleCount : '-' }} 名
            </span>
            <span class="badge bg-secondary d-flex align-items-center gap-2">
              <IconClock size="16" /> {{ openedAt || '--:--' }} – {{ endedAt || '—' }}
            </span>
          </div>
          <div class="current-table">
            <span class="text-bg-success p-2 d-flex align-items-center justify-content-center w-100 gap-2 rounded">
              <IconPinned /> <span class="fs-1">{{ tableLabel }}</span>
            </span>
          </div>
        </div>

        <!-- 注文 -->
        <OrderPanelSP
          v-if="pane==='order'"
          :cat-options="catOptionsArr"
          :selected-cat="selectedCatVal"
          :order-masters="orderMastersArr"
          :served-by-options="servedByOptionsArr"
          v-model:served-by-cast-id="servedByCastIdModel"
          :pending="pendingArr"
          :master-name-map="masterNameMap"
          :served-by-map="servedByMap"
          :master-price-map="masterPriceMap"
          @update:selectedCat="v => (selectedCatVal = v)"
          @addPending="addPending"
          @removePending="removePending"
          @clearPending="clearPending"
          @placeOrder="placeOrder"
        />

        <!-- 会計 -->
        <PayPanelSP
          v-else-if="pane==='pay'"
          :items="currentBill?.items || []"
          :master-name-map="masterNameMap"
          :served-by-map="servedByMap"
          :bill-opened-at="currentBill?.opened_at || ''"
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

        <ProvisionalPanelSP
          v-else
          :key="`prov-${targetBillId}`"
          :bill="currentBill || {}"
          :ed="ed"
          :service-rate="0.3"
          :tax-rate="0.1"
        />

      </div>
    </template>

    <div class="order-footer">
      <div class="nav nav-pills nav-fill small gap-2 pills-flat">
        <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='order'}" @click="pane='order'">
          <IconShoppingCart />
          <span>注文</span>
        </button>
        <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='pay'}" @click="pane='pay'">
          <IconReceiptYen />
          <span>会計</span>
        </button>
        <button type="button" class="nav-link d-flex flex-column" :class="{active: pane==='kari'}" @click="pane='kari'">
          <IconCalculator />
          <span>仮</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>

.order-footer{
  position: fixed; left: 0; right: 0; bottom: 0;
  background: #fff; border-top: 1px solid #eee;
  padding: .5rem max(env(safe-area-inset-left), .75rem)
           calc(.5rem + env(safe-area-inset-bottom))
           max(env(safe-area-inset-right), .75rem);
  z-index: 1040;
}
.cast-order-page{ padding-bottom: 88px; }
.pills-flat{ --bs-nav-pills-link-active-bg:#fff; --bs-nav-pills-link-active-color:#000; }
.pills-flat .nav-link{ background:#fff; color:#a9a9a9; border-radius:.75rem; }
.pills-flat .nav-link.active{ color:#000; font-weight:700; }
</style>
