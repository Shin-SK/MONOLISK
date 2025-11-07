<script setup>
import { ref, watch, computed, onMounted, nextTick } from 'vue'
import dayjs from 'dayjs'
import { fetchDiscountRules } from '@/api'

const props = defineProps({
  items: { type: Array, default: () => [] },
  masterNameMap: { type: Object, default: () => ({}) },
  servedByMap:   { type: Object, default: () => ({}) },
  current: { type: Object, default: () => ({ sub:0, svc:0, tax:0, total:0 }) },
  displayGrandTotal: { type: Number, default: 0 },
  settledTotal: { type: Number, default: 0 },
  paidCash:     { type: Number, default: 0 },
  paidCard:     { type: Number, default: 0 },
  billOpenedAt: { type: String, default: '' },
  diff:     { type: Number, default: 0 },
  overPay:  { type: Number, default: 0 },
  canClose: { type: Boolean, default: false },
  memo: { type: String, default: '' },
  discountRuleId: { type: [Number, null], default: null },
})
const emit = defineEmits([
  'update:settledTotal','update:paidCash','update:paidCard',
  'fillRemainderToCard','confirmClose','incItem','decItem','deleteItem',
  'update:discountRule',
])

const dirtyTotal = ref(false)
const hasExistingPayment = computed(() => {
  const c = Number(props.paidCash || 0)
  const k = Number(props.paidCard || 0)
  return (c + k) > 0
})

onMounted(() => {
  if (hasExistingPayment.value) {
    dirtyTotal.value = true
  }
})

watch(
  () => props.current.total,
  (v) => {
    if (dirtyTotal.value || hasExistingPayment.value) return
    const n = Number(v ?? 0)
    emit('update:settledTotal', Number.isFinite(n) ? n : 0)
  },
  { immediate: true }
)

/* 時刻表示など */
const pickTime = (it) =>
  it?.ordered_at || it?.served_at || it?.created_at || it?.updated_at || props.billOpenedAt || null
const fmtTime  = (t) => t ? dayjs(t).format('YYYY/M/D HH:mm') : ''

/* ===== 割引 ===== */
const discountRules = ref([{ id: null, name: '割引なし', amount_off: null, percent_off: null }])
const selectedDiscountId = ref(null)
const discountRuleMap = ref(new Map())

onMounted(async () => {
  try {
    const list = await fetchDiscountRules({ is_active: true, place: 'pay' })
    const arr = (Array.isArray(list) ? list : [])
      .filter(r => r && r.id != null && r.name)
      .map(r => ({
        id: Number(r.id),
        name: String(r.name),
        code: r.code || null,
        amount_off: r.amount_off ? Number(r.amount_off) : null,
        percent_off: r.percent_off ? Number(r.percent_off) : null,
      }))
    arr.forEach(rule => discountRuleMap.value.set(rule.id, rule))
    discountRules.value = [{ id: null, name: '割引なし', amount_off: null, percent_off: null }, ...arr]
    selectedDiscountId.value = props.discountRuleId ? Number(props.discountRuleId) : null
  } catch (e) {
    console.warn('[PayPanel] load rules failed', e)
    discountRules.value = [{ id: null, name: '割引なし', amount_off: null, percent_off: null }]
    selectedDiscountId.value = null
  }
})

const totalBeforeDiscount = computed(() => {
  const sub = Number(props.current?.sub || 0)
  const svc = Number(props.current?.svc || 0)
  const tax = Number(props.current?.tax || 0)
  return sub + svc + tax
})

const discountAmount = computed(() => {
  if (!selectedDiscountId.value) return 0
  const rule = discountRuleMap.value.get(selectedDiscountId.value)
  if (!rule) return 0
  if (rule.amount_off != null) return rule.amount_off
  if (rule.percent_off != null) {
    const rate = rule.percent_off >= 1 ? rule.percent_off / 100 : rule.percent_off
    return Math.floor(totalBeforeDiscount.value * rate)
  }
  return 0
})

function calculateDiscountedTotal() {
  return Math.max(0, totalBeforeDiscount.value - discountAmount.value)
}
const discountedTotal = computed(() => calculateDiscountedTotal())

const displayTotalAfterDiscount = computed(() => {
  const st = Number(props.settledTotal || 0)
  return st > 0 ? st : discountedTotal.value
})

const needsUpdate = computed(() =>
  dirtyTotal.value || Number(props.settledTotal || 0) !== discountedTotal.value
)

function updateSettledWithDiscount() {
  if (dirtyTotal.value || hasExistingPayment.value) return
  emit('update:settledTotal', calculateDiscountedTotal())
}

function onDiscountChange(e) {
  const selectedId = e.target.value === '' ? null : Number(e.target.value)
  selectedDiscountId.value = selectedId
  updateSettledWithDiscount()
  emit('update:discountRule', selectedId)
}

watch(() => props.discountRuleId, (newId) => {
  const newIdNum = newId ? Number(newId) : null
  if (selectedDiscountId.value !== newIdNum) {
    selectedDiscountId.value = newIdNum
    nextTick(() => updateSettledWithDiscount())
  }
}, { immediate: true })

/* 入出力モデル */
const toNum = (v) => {
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : 0
}
const settled = computed({
  get: () => toNum(props.settledTotal),
  set: (v) => { dirtyTotal.value = true; emit('update:settledTotal', toNum(v)) }
})
const paidCashModel = computed({
  get: () => toNum(props.paidCash),
  set: (v) => emit('update:paidCash', toNum(v))
})
const paidCardModel = computed({
  get: () => toNum(props.paidCard),
  set: (v) => emit('update:paidCard', toNum(v))
})

const setExactCash = () => {
  const total = Math.max(0, toNum(settled.value))
  emit('update:paidCash', total)
  emit('update:paidCard', 0)
}
const setExactCard = () => {
  const total = Math.max(0, toNum(settled.value))
  emit('update:paidCash', 0)
  emit('update:paidCard', total)
}

/* メモ */
const memoLocal = ref(String(props.memo ?? ''))
watch(() => props.memo, v => { memoLocal.value = String(v ?? '') })
const getMemo = () => String(memoLocal.value || '')
defineExpose({ getMemo })
</script>

<template>
<div class="panel pay">
  <div class="d-flex flex-column gap-4">
    <!-- 履歴 -->
    <div class="history-list d-flex flex-column gap-3">
      <div v-for="it in items" :key="it.id" class="card bg-light d-flex flex-row justify-content-between">
        <div class="item-area p-2 d-flex flex-column gap-2 flex-grow-1">
          <div class="d-flex align-items-center gap-2 text-secondary" style="font-size:1rem;">
            <div class="id">#{{ it.id }}</div>
            <div class="time d-flex align-items-center gap-1 small text-muted">
              <IconClock :size="16" />{{ fmtTime(pickTime(it)) }}
            </div>
          </div>
          <div class="d-flex align-items-center gap-3 flex-wrap">
            <div class="name fs-5 fw-bold">
              {{ it.name || masterNameMap[String(it.item_master)] || ('#'+it.item_master) }}
            </div>
            <div class="price">¥{{ (it.subtotal ?? 0).toLocaleString() }}</div>
          </div>
          <div class="cast d-flex align-items-center gap-1">
            <IconUser :size="16" />
            {{ it.served_by_cast?.stage_name || servedByMap[String(it.served_by_cast_id)] || '—' }}
          </div>
        </div>
        <div class="d-flex align-items-center">
          <div class="cartbutton d-flex align-items-center">
            <div class="d-flex align-items-center gap-3 bg-white h-auto p-2 m-2" style="border-radius:100px;">
              <button type="button" @click="$emit('decItem', it)"><IconMinus :size="16" /></button>
              <span>{{ it.qty }}</span>
              <button type="button" @click="$emit('incItem', it)"><IconPlus :size="16" /></button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="!items || !items.length" class="text-muted small">履歴はありません</div>
    </div>

    <!-- 割引 -->
    <div class="coupon">
      <label class="form-label fw-bold">割引</label>
      <select class="form-select" :value="selectedDiscountId" @change="onDiscountChange">
        <option v-for="rule in discountRules" :key="rule.id ?? 'none'" :value="rule.id ?? ''">
          {{ rule.name }}
        </option>
      </select>
    </div>

    <!-- サマリ -->
    <div class="sum">
      <div class="d-grid gap-3" style="grid-template-columns: 1fr auto;">
        <div class="label">小計</div>      <div class="value text-end">¥{{ current.sub.toLocaleString() }}</div>
        <div class="label">サービス料</div><div class="value text-end">¥{{ current.svc.toLocaleString() }}</div>
        <div class="label">TAX</div>    <div class="value text-end">¥{{ current.tax.toLocaleString() }}</div>
        <div class="label fw-bold fs-5">合計</div><div class="value fw-bold text-end fs-5">¥{{ current.total.toLocaleString() }}</div>
        <template v-if="discountAmount > 0">
          <div class="label text-danger">割引</div><div class="value text-end text-danger">-¥{{ discountAmount.toLocaleString() }}</div>
          <div class="label fw-bold">割引後</div><div class="value fw-bold text-end">¥{{ discountedTotal.toLocaleString() }}</div>
        </template>
      </div>
    </div>

    <!-- 支払い -->
    <div class="payment d-flex flex-column gap-3">
      <div class="d-flex">
        <label class="d-flex align-items-center" style="width: 100px;">会計金額</label>
        <div class="position-relative w-100">
          <input class="form-control" type="number" v-model="settled" />
          <button v-if="needsUpdate" class="position-absolute top-0 bottom-0 end-0 px-2" type="button"
                  @click="updateSettledWithDiscount" title="割引適用後の金額に合わせる">
            <IconRefresh :size="16"/>
          </button>
        </div>
      </div>

      <div class="d-flex">
        <label class="d-flex align-items-center" style="width: 100px;">現金</label>
        <div class="position-relative w-100">
          <input class="form-control" type="number" v-model="paidCashModel" />
          <button class="position-absolute end-0 top-0 bottom-0" type="button" @click="setExactCash" title="全額を現金で支払い">
            <IconTransferVertical :size="16" />
          </button>
        </div>
      </div>

      <div class="d-flex">
        <label class="d-flex align-items-center" style="width: 100px;">カード</label>
        <div class="position-relative w-100">
          <input class="form-control" type="number" v-model="paidCardModel" />
          <button class="position-absolute end-0 top-0 bottom-0" type="button" @click="$emit('fillRemainderToCard')">
            <IconCalculator :size="16" />
          </button>
        </div>
      </div>

      <div class="small text-muted">
        会計金額: ¥{{ discountedTotal.toLocaleString() }} /
        受領合計: ¥{{ (Number(paidCash||0)+Number(paidCard||0)).toLocaleString() }} /
        差額: <span :class="diff===0 ? 'ok' : 'neg'">¥{{ diff.toLocaleString() }}</span>
        <span v-if="overPay>0" class="text-danger ms-1">（お釣り: ¥{{ overPay.toLocaleString() }}）</span>
      </div>
    </div>

    <!-- メモ -->
    <div class="memo">
      <label class="form-label">メモ</label>
      <textarea class="form-control" rows="3" v-model="memoLocal" placeholder="伝票メモ（備考）"></textarea>
    </div>

    <!-- 確定 -->
    <div class="paybutton">
      <button class="btn btn-primary w-100" type="button" :disabled="!canClose" @click="$emit('confirmClose')">お会計</button>
    </div>
  </div>
</div>
</template>
