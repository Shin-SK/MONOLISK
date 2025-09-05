<script setup>
import { ref, computed, watch } from 'vue'
import dayjs from 'dayjs'
import OrderPanelSP from '@/components/spPanel/OrderPanelSP.vue'

const props = defineProps({
  bill: { type: Object, required: true },          // currentBill
  masters: { type: Array, default: () => [] },     // フォールバック用
  ed: { type: Object, default: null },             // ★ 追加：useBillEditor を丸ごと渡す
  serviceRate: { type: Number, default: 0.3 },
  taxRate: { type: Number, default: 0.1 },
})

/* ===== データソース（ed優先） ===== */
const srcMasters = computed(() => props.ed?.masters?.value ?? props.masters)

/* ===== ヘルパ ===== */
const priceOf = (id) => {
  const m = srcMasters.value.find(x => x?.id === id)
  return Number(m?.price_regular ?? m?.price ?? 0)
}
const nameOf = (id) => srcMasters.value.find(x => x?.id === id)?.name || `#${id}`

function calcTotals(items) {
  const sub = items.reduce((s, it) => {
    const unit = Number(it.price ?? priceOf(it.item_master))
    return s + unit * (Number(it.qty) || 0)
  }, 0)
  const svc = Math.round(sub * (props.serviceRate || 0))
  const tax = Math.round((sub + svc) * (props.taxRate || 0))
  return { sub, svc, tax, total: sub + svc + tax }
}

/* ===== 既存伝票 → 基準 ===== */
const baseItems = computed(() => {
  const src = Array.isArray(props.bill?.items) ? props.bill.items : []
  return src.map(it => ({
    item_master: it.item_master,
    qty: Number(it.qty) || 0,
    price: it.price ?? null,
    duration_min: it.duration_min || 0,
    name: it.name || nameOf(it.item_master),
  }))
})
const baseTotals = computed(() => calcTotals(baseItems.value))
const baseEndAt = computed(() => {
  const opened = props.bill?.opened_at ? dayjs(props.bill.opened_at) : null
  if (!opened) return null
  if (props.bill?.expected_out) return dayjs(props.bill.expected_out)
  const mins = baseItems.value.reduce((s, it) => s + (Number(it.duration_min)||0) * (Number(it.qty)||1), 0)
  return opened.add(mins, 'minute')
})

/* ===== UI状態 ===== */
const show = ref(true)
const tab  = ref('ext')   // 'ext' | 'order'

/* ===== 延長タブ：ラジオ/ボタン式 ===== */
/* duration_min>0 の商品を抽出。ボタンで選択→「＋1回」で extCount を加算 */
const extMasterId = ref(null)
const extCount    = ref(0)            // ← 初期0、ボタンで増える
const extOptions = computed(() =>
  (srcMasters.value || [])
    .filter(m => Number(m?.duration_min) > 0)
    .map(m => ({ id: m.id, label: m.name, mins: Number(m.duration_min)||0 }))
)

// 1タップで「選択＆1回追加」
function pickExtOnce(id){
  if (extMasterId.value !== id) extMasterId.value = id
  extCount.value = (Number(extCount.value)||0) + 1
}
function clearExt(){ extMasterId.value = null; extCount.value = 0 }

/* ===== 注文タブ（OrderPanelSPを“仮モード”で再利用） ===== */
/* edをそのまま使う（cat/masters/selectedCat）。仮カートだけローカル */
const catOptions = computed(() => props.ed?.orderCatOptions?.value ?? [])
// ★ edのカテゴリ選択をそのまま共有（UI連動を優先）
const selectedCat = computed({
  get: () => props.ed?.selectedOrderCat?.value ?? null,
  set: v  => { if (props.ed?.selectedOrderCat) props.ed.selectedOrderCat.value = v }
})
const orderMasters = computed(() => props.ed?.orderMasters?.value ?? srcMasters.value)
const servedByOptions = computed(()=> [{ id:null, label:'未指定' }])  // 仮なので未指定のみ
const servedByCastId  = ref(null)
const pending         = ref([])  // ← 仮注文カート（APIへは送らない）

const masterNameMap  = computed(() => Object.fromEntries((srcMasters.value||[]).map(m => [String(m.id), m.name])))
const masterPriceMap = computed(() => Object.fromEntries((srcMasters.value||[]).map(m => [String(m.id), Number(m.price_regular ?? m.price ?? 0)])))
const servedByMap    = computed(() => ({ 'null':'未指定' }))

function addPending(masterId, qty){ pending.value.push({ master_id: masterId, qty, cast_id: null }) }
function removePending(i){ pending.value.splice(i,1) }
function clearPending(){ pending.value = [] }

/* ===== 手動円加算 ===== */
const manualYen = ref(0)

/* ===== 仮アイテム／計算 ===== */
const hypoItems = computed(() => {
  const out = [...baseItems.value.map(({item_master, qty, price}) => ({item_master, qty, price}))]

  // 延長
  if (extMasterId.value && Number(extCount.value) > 0) {
    out.push({ item_master: Number(extMasterId.value), qty: Number(extCount.value) })
  }
  // 仮追加
  for (const p of pending.value) {
    out.push({ item_master: Number(p.master_id), qty: Number(p.qty) })
  }
  // 手動加算
  if (Number(manualYen.value) > 0) {
    out.push({ item_master: 0, qty: 1, price: Number(manualYen.value) })
  }
  return out
})
const hypoTotals = computed(() => calcTotals(hypoItems.value))
const deltaTotal = computed(() => hypoTotals.value.total - baseTotals.value.total)
// ▼ pending内の「時間系商品」分の延長（duration_min×qty）
const pendingExtMins = computed(() => {
  const list = Array.isArray(pending.value) ? pending.value : []
  return list.reduce((sum, p) => {
    const mm = srcMasters.value.find(x => x?.id === Number(p.master_id))
    const mins = Number(mm?.duration_min) || 0
    return sum + mins * (Number(p.qty) || 0)
  }, 0)
})
// ▼ extボタンで選んだ延長（使っていない場合は0）
const extMins = computed(() => {
  const m = srcMasters.value.find(x => x?.id === Number(extMasterId.value))
  return ((Number(m?.duration_min)||0) * (Number(extCount.value)||0)) || 0
})
// ▼ 仮の終了時刻 = 現在ベース + pending分 + extボタン分
const hypoEndAt  = computed(() => {
  if (!baseEndAt.value) return null
  return baseEndAt.value.add(pendingExtMins.value + extMins.value, 'minute')
})

function resetAll(){
  clearExt()
  pending.value = []
  manualYen.value = 0
}
</script>

<template>
  <div class="card border-0 shadow-sm mt-3">
    <div class="card-header bg-white p-3 d-flex justify-content-center align-items-center">
      <div class="fw-bold fs-5">仮会計（保存されません）</div>
    </div>

    <div class="card-body bg-white">

      <!-- 追加注文：OrderPanelSP（APIは呼ばず、pendingのみ反映） -->
      <div class="mb-4">
        <OrderPanelSP
          :cat-options="catOptions"
          :selected-cat="selectedCat"
          :order-masters="orderMasters"
          :served-by-options="servedByOptions"
          v-model:served-by-cast-id="servedByCastId"
          :pending="pending"
          :master-name-map="masterNameMap"
          :served-by-map="servedByMap"
          :master-price-map="masterPriceMap"
          :readonly="true"
          @update:selectedCat="v => (selectedCat = v)"
          @addPending="addPending"
          @removePending="removePending"
          @clearPending="clearPending"
          @placeOrder="() => {}"
        />
      </div>

      <!-- 手動円加算 -->
      <div class="mb-4">
        <label class="form-label">手動金額を加算（¥）</label>
        <input type="number" class="form-control" v-model.number="manualYen" min="0" placeholder="0">
        <div class="form-text">※税・サ込みで合計に直で加算します（微調整用）。</div>
      </div>

      <hr>

      <!-- サマリ -->
      <div class="summary">
        <div class="wrapper mb-3">
          <div class="my-5">
            <div class="d-flex justify-content-between fs-4">
              <span class="fw-bold">仮の合計</span><strong>¥{{ hypoTotals.total.toLocaleString() }}</strong>
            </div>
            <div class="d-flex align-items-center justify-content-between my-3">
              <div class="d-flex align-items-center gap-2">
                <IconDatabase />
                <span>
                {{ hypoTotals.sub.toLocaleString() }} + サ¥{{ hypoTotals.svc.toLocaleString() }} + 税¥{{ hypoTotals.tax.toLocaleString() }}
                </span>
              </div>
              <div class="d-flex align-items-center gap-2">
                <span class="badge bg-secondary">差額</span>
                <strong :class="{'text-danger': deltaTotal>0, 'text-success': deltaTotal<=0}">
                  ¥{{ deltaTotal.toLocaleString() }}
                </strong>
              </div>
            </div>
            <div class="d-flex align-items-center gap-2">
              <IconAlarm />
              <strong>{{ hypoEndAt ? hypoEndAt.format('HH:mm') : '—' }}</strong>
            </div>

          </div>
        </div>
        <div class="wrapper">
          <div class="p-3 bg-light rounded">
            <div class="d-flex justify-content-between">
              <span>現在の合計</span><strong>¥{{ baseTotals.total.toLocaleString() }}</strong>
            </div>
            <div class="text-muted small">
              小計¥{{ baseTotals.sub.toLocaleString() }} + サ¥{{ baseTotals.svc.toLocaleString() }} + 税¥{{ baseTotals.tax.toLocaleString() }}
            </div>
            <div class="mt-2">
              終了予定：<strong>{{ baseEndAt ? baseEndAt.format('HH:mm') : '—' }}</strong>
            </div>
          </div>
        </div>
      </div><!-- /summary -->

      <div class="mt-5 d-flex gap-2 flex-column">
        <button class="btn btn-outline-secondary" @click="resetAll">リセット</button>
        <div class="form-text">※結果は保存されません。実際に追加する場合は「注文」から確定してください。</div>
      </div>
    </div>
  </div>
</template>
