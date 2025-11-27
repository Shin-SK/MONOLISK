<script setup>
import { ref, watch, computed, onMounted, nextTick } from 'vue'
import dayjs from 'dayjs'
import { fetchDiscountRules } from '@/api'

/* ---------------------------------------------------------
 * Props / Emits
 * --------------------------------------------------------- */
const props = defineProps({
  // 履歴・表示用
  items: { type: Array, default: () => [] },
  masterNameMap: { type: Object, default: () => ({}) },
  servedByMap:   { type: Object, default: () => ({}) },

  // 金額（サーバ計算の転送値）
  current: { type: Object, default: () => ({ sub:0, svc:0, tax:0, total:0 }) },
  displayGrandTotal: { type: Number, default: 0 },

  // 入力モデル（v-model:風に双方向）
  settledTotal: { type: Number, default: 0 },
  paidCash:     { type: Number, default: 0 },
  paidCard:     { type: Number, default: 0 },

  // 表示補助
  billOpenedAt: { type: String, default: '' },
  diff:     { type: Number, default: 0 },
  overPay:  { type: Number, default: 0 },
  canClose: { type: Boolean, default: false },

  // 備考
  memo: { type: String, default: '' },

  // 割引（サーバ側の単発適用用）
  discountRuleId: { type: [Number, null], default: null },
  // 保存済み手入力割引（再初期化用）
  manualDiscounts: { type: Array, default: () => [] },

  // 店舗識別（親から slug を渡す）
  storeSlug: { type: String, default: '' },

  // （互換）単位指定：現行の“ステップ割引”では Admin 側ルールを使うため未使用だが props として残す
  dosukoiDiscountUnit: { type: Number, default: 1000 },
})

const emit = defineEmits([
  'update:settledTotal',
  'update:paidCash',
  'update:paidCard',
  'fillRemainderToCard',
  'confirmClose',
  'incItem',
  'decItem',
  'deleteItem',
  'update:discountRule',
  'saveDiscount',
])

/* ---------------------------------------------------------
 * 初期状態 / ユーティリティ
 * --------------------------------------------------------- */
const dirtyTotal = ref(false)

const hasExistingPayment = computed(() => {
  const c = Number(props.paidCash || 0)
  const k = Number(props.paidCard || 0)
  return (c + k) > 0
})

onMounted(() => {
  if (hasExistingPayment.value) dirtyTotal.value = true
})

/* 時刻表示など（履歴カード用） */
const pickTime = (it) =>
  it?.ordered_at || it?.served_at || it?.created_at || it?.updated_at || props.billOpenedAt || null
const fmtTime  = (t) => t ? dayjs(t).format('YYYY/M/D HH:mm') : ''

/* ---------------------------------------------------------
 * 会計金額の自動追従（サーバ計算→クライアント settledTotal へ）
 * --------------------------------------------------------- */
watch(
  () => props.current.total,
  (v) => {
    if (dirtyTotal.value || hasExistingPayment.value) return
    const n = Number(v ?? 0)
    emit('update:settledTotal', Number.isFinite(n) ? n : 0)
  },
  { immediate: true }
)

/* ---------------------------------------------------------
 * 割引ルール（共通）：/api から取得
 *  - discountRules: 画面用の配列（先頭に「割引なし」）
 *  - discountRuleMap: id → ルール の解決
 *  - selectedDiscountId: <select> の選択 id
 * --------------------------------------------------------- */
const discountRules = ref([{ id: null, name: '割引なし', amount_off: null, percent_off: null }])
const selectedDiscountId = ref(null)
const discountRuleMap = ref(new Map())

onMounted(async () => {
  try {
    const list = await fetchDiscountRules({ is_active: true, place: 'pay' })
    const arr = (Array.isArray(list) ? list : [])
      .filter(r => r && r.id != null && r.name)
      .sort((a,b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)) // 並び順：任意
      .map(r => ({
        id: Number(r.id),
        name: String(r.name),
        code: r.code || null,
        amount_off: r.amount_off != null ? Number(r.amount_off) : null,
        percent_off: r.percent_off != null ? Number(r.percent_off) : null,
      }))
    arr.forEach(rule => discountRuleMap.value.set(rule.id, rule))
    discountRules.value = [{ id: null, name: '割引なし', amount_off: null, percent_off: null }, ...arr]
    selectedDiscountId.value = props.discountRuleId ? Number(props.discountRuleId) : null
  } catch (e) {
    console.warn('[PayPanel] load rules failed', e)
    discountRules.value = [{ id: null, name: '割引なし', amount_off: null, percent_off: null }]
    selectedDiscountId.value = null
  }

  // 保存済み割引の復元（初回マウント時のみ）
  hydrateManualDiscounts()
})

// 保存済み割引の初期化(両モード共通: savedDiscountRowsに復元)
function hydrateManualDiscounts() {
  const saved = props.manualDiscounts || []
  if (!saved.length) return
  
  // 保存済み割引を個別行として復元
  savedDiscountRows.value = saved.map((r, i) => ({
    id: `saved-${i}`,
    label: String(r.label || ''),
    amount: Number(r.amount || 0),
  })).filter(r => r.label && r.amount > 0)
}

/* ---------------------------------------------------------
 * ドスコイ方式：Adminの金額割引（amount_off）を“ステップ”化
 *  - stepRules: 金額割引のみ抽出（%は除外）
 *  - dosukoiQtyMap: { ruleId: 数量 } の可変 Map
 *  - dosukoiDiscountAmount: Σ (qty × amount_off)
 *  - incStep/decStep: 数量変更
 *  - 数量変更時、割引後合計へ自動追従
 * --------------------------------------------------------- */
const stepRules = computed(() =>
  (discountRules.value || [])
    .filter(r => Number(r.amount_off) > 0 && (r.percent_off == null))
    .sort((a, b) => Number(a.amount_off || 0) - Number(b.amount_off || 0)) // 金額昇順
)

const dosukoiQtyMap = ref({})

watch(stepRules, (list) => {
  const next = { ...dosukoiQtyMap.value }
  for (const r of list) if (next[r.id] == null) next[r.id] = 0
  for (const k of Object.keys(next)) if (!list.find(r => String(r.id) === String(k))) delete next[k]
  dosukoiQtyMap.value = next
}, { immediate: true })

const dosukoiDiscountAmount = computed(() =>
  stepRules.value.reduce((s, r) => {
    const q = Number(dosukoiQtyMap.value[r.id] || 0)
    const a = Number(r.amount_off || 0)
    return s + (q * a)
  }, 0)
)

function incStep(ruleId) {
  dosukoiQtyMap.value[ruleId] = Math.max(0, Number(dosukoiQtyMap.value[ruleId] || 0) + 1)
}
function decStep(ruleId) {
  dosukoiQtyMap.value[ruleId] = Math.max(0, Number(dosukoiQtyMap.value[ruleId] || 0) - 1)
}

watch(dosukoiQtyMap, () => {
  if (isDosukoiMode.value) updateSettledWithDiscount()
}, { deep: true })

// ▼ ドスコイ割引用アコーディオン開閉
const showDiscountPanel = ref(false)

// 初期状態：数量が1つでも入っていれば自動で開く
watch([stepRules, dosukoiQtyMap], () => {
  const hasQty = stepRules.value.some(r => Number(dosukoiQtyMap.value[r.id] || 0) > 0)
  if (hasQty) showDiscountPanel.value = true
}, { immediate: true, deep: true })

function toggleDiscountPanel() {
  showDiscountPanel.value = !showDiscountPanel.value
}

/* ---------------------------------------------------------
 * 割引の共通計算
 *  - totalBeforeDiscount: 割引前の合計（sub+svc+tax）
 *  - 店舗分岐：slug → features（dosukoi-asa: step）
 *  - discountAmount: 店舗分岐ごとの割引額
 *  - discountedTotal: 割引後合計
 * --------------------------------------------------------- */
const totalBeforeDiscount = computed(() => {
  const sub = Number(props.current?.sub || 0)
  const svc = Number(props.current?.svc || 0)
  const tax = Number(props.current?.tax || 0)
  return sub + svc + tax
})

/* 店舗分岐（必要に応じて STORE_FEATURES に追加） */
const normSlug = computed(() =>
  String(props.storeSlug).trim().toLowerCase().replace(/_/g, '-')
)
const STORE_FEATURES = Object.freeze({
  'dosukoi-asa': { discountMode: 'step' }, // ステップ方式
})
const features = computed(() => STORE_FEATURES[normSlug.value] || { discountMode: 'rule' })
const isDosukoiMode = computed(() => features.value.discountMode === 'step')

/* 割引額(店舗分岐) */
const savedDiscountAmount = computed(() => 
  savedDiscountRows.value.reduce((s, r) => s + Number(r.amount || 0), 0)
)

const discountAmount = computed(() => {
  // 保存済み割引(両モード共通)
  let total = savedDiscountAmount.value
  
  // ドスコイ:ステップ合計を追加
  if (isDosukoiMode.value) {
    total += dosukoiDiscountAmount.value
    return total
  }

  // 通常モード:手入力があれば追加
  if (manualDiscountAmount.value > 0) {
    total += manualDiscountAmount.value
    return total
  }

  // それ以外は(残すなら)選択ルールを適用
  if (!selectedDiscountId.value) return total
  const rule = discountRuleMap.value.get(selectedDiscountId.value)
  if (!rule) return total
  if (rule.amount_off != null) return total + rule.amount_off
  if (rule.percent_off != null) {
    const rate = rule.percent_off >= 1 ? rule.percent_off / 100 : rule.percent_off
    return total + Math.floor(totalBeforeDiscount.value * rate)
  }
  return total
})

function calculateDiscountedTotal() {
  return Math.max(0, totalBeforeDiscount.value - discountAmount.value)
}
const discountedTotal = computed(() => calculateDiscountedTotal())

/* 表示値（会計金額入力がある場合はそちら優先） */
const displayTotalAfterDiscount = computed(() => {
  const st = Number(props.settledTotal || 0)
  return st > 0 ? st : discountedTotal.value
})

/* 割引変更 → 会計金額を追従（dirty/入金済なら追従しない） */
const needsUpdate = computed(() =>
  dirtyTotal.value || Number(props.settledTotal || 0) !== discountedTotal.value
)
function updateSettledWithDiscount() {
  if (dirtyTotal.value || hasExistingPayment.value) return
  emit('update:settledTotal', calculateDiscountedTotal())
}

/* 単発<select>の値をサーバ保持と同期（外部から変えられた時も追従） */
function onDiscountChange(e) {
  if (isDosukoiMode.value) return
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

/* ---------------------------------------------------------
 * 割引手入力
 * --------------------------------------------------------- */
function getManualDiscounts() {
  if (isDosukoiMode.value) {
    return stepRules.value
      .map((r, i) => {
        const q = Number(dosukoiQtyMap.value[r.id] || 0)
        const amt = Number(r.amount_off || 0) * q
        if (q <= 0 || amt <= 0) return null
        const name = r.name || `¥${Number(r.amount_off).toLocaleString()}`
        return { label: `${name} ×${q}`, amount: amt, sort_order: r.sort_order ?? i }
      })
      .filter(Boolean)
  }
  // 通常：手入力
  return (manualRows.value || [])
    .map((r, i) => {
      const label = (r.label || '').trim()
      const amount = num(r.amount)
      if (!label || amount <= 0) return null
      return { label, amount, sort_order: i }
    })
    .filter(Boolean)
}

/* ===== 手入力割引(通常モード用) ===== */
const useManualGlobal = ref(false)                   // 入力欄の開閉スイッチ
const manualRows = ref([{ label: '', amount: 0 }])  // 初期1行

// 保存済み割引(確定済みの行リスト: 両モード共通)
const savedDiscountRows = ref([])

function addManualRow(){ manualRows.value.push({ label:'', amount:0 }) }
function removeManualRow(i){
  manualRows.value.splice(i,1)
  if (!manualRows.value.length) manualRows.value.push({ label:'', amount:0 })
}
const num = v => {
  const n = typeof v === 'number' ? v : Number(String(v).replace(/[^\d.-]/g,''))
  return Number.isFinite(n) ? n : 0
}
const manualDiscountAmount = computed(() =>
  manualRows.value.reduce((s, r) => s + Math.max(0, num(r.amount)), 0)
)


// ① 手入力（manualRows）が変わったら即追従（通常モードだけ）
watch(manualRows, () => {
  if (!isDosukoiMode.value) updateSettledWithDiscount()
}, { deep: true })

// ② 割引額そのもの or 前提合計が変わったら追従（ドスコイ含む）
//   ※ dirty/既入金時は updateSettledWithDiscount 内で抑止済み
watch([discountAmount, totalBeforeDiscount], () => {
  updateSettledWithDiscount()
})



/* ---------------------------------------------------------
 * 入出力モデル（v-model:風の双方向バインド）
 * --------------------------------------------------------- */
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

/* ワンタップで全額現金/カードに割り当て */
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

/* ---------------------------------------------------------
 * メモ（Expose）
 * --------------------------------------------------------- */
const memoLocal = ref(String(props.memo ?? ''))
watch(() => props.memo, v => { memoLocal.value = String(v ?? '') })
const getMemo = () => String(memoLocal.value || '')

/* 親へ割引明細を返すエクスポート関数
 * - ドスコイ：¥1,000×2, ¥500×1 のような内訳をラベル化
 * - 通常   ：選択ルール名と割引額
 */
const getDiscountEntry = () => {
  if (isDosukoiMode.value) {
    const parts = stepRules.value
      .map(r => ({ r, q: Number(dosukoiQtyMap.value[r.id] || 0) }))
      .filter(x => x.q > 0)
      .map(x => `¥${Number(x.r.amount_off).toLocaleString()}×${x.q}`)
    const label = parts.length ? `手動（${parts.join(', ')}）` : '手動（なし）'
    return { label, amount: dosukoiDiscountAmount.value }
  }
  if (manualDiscountAmount.value > 0) {
    const parts = (manualRows.value || [])
      .filter(r => num(r.amount) > 0 && (r.label || '').trim())
      .map(r => `${r.label} ¥${num(r.amount).toLocaleString()}`)
    const label = parts.length ? `手入力（${parts.join(', ')}）` : '手入力（なし）'
    return { label, amount: manualDiscountAmount.value }
  }
  const id = selectedDiscountId.value
  const rule = id ? discountRuleMap.value.get(id) : null
  return { label: rule?.name || '割引なし', amount: discountAmount.value }
}

/* ---------------------------------------------------------
 * 伝票切替時の内部状態リセット
 *  - コンポーネントは再利用されるため A→B 切替で前回の dirtyTotal / 手入力割引が残る
 *  - billOpenedAt (親から渡される伝票開始時刻) の変化をトリガに初期化
 *  - 必要なら将来 billId を props 化してそちらをキーにしても良い
 * --------------------------------------------------------- */
function resetStateForNewBill() {
  dirtyTotal.value = false
  // 手入力割引行を初期化
  manualRows.value = [{ label: '', amount: 0 }]
  // ステップ割引数量クリア(店舗モード差異あり)
  dosukoiQtyMap.value = {}
  // 保存済み割引をクリア
  savedDiscountRows.value = []
  // 割引選択を props.discountRuleId に再同期
  selectedDiscountId.value = props.discountRuleId ? Number(props.discountRuleId) : null
  // 自動で開かないよう閉じる(必要なら条件付き可)
  showDiscountPanel.value = false
  // 再計算を強制(dirtyTotal解除後)
  nextTick(() => updateSettledWithDiscount())
}

let _prevBillOpenedAt = props.billOpenedAt || null
watch(() => props.billOpenedAt, (now) => {
  if (!now) return
  if (_prevBillOpenedAt !== now) {
    resetStateForNewBill()
    _prevBillOpenedAt = now
  }
})

/* 会計金額表示は割引適用後の最終確定見込み値を優先
 * discountedTotal は常に再計算値 / settledTotal がユーザ編集済ならそちら優先
 * 既存 small 行で discountedTotal を直接使っているため保持
 */

defineExpose({ getMemo, getDiscountEntry, getManualDiscounts })

/* ---------------------------------------------------------
 * 保存ボタン（親に保存イベントを通知）
 *  - 通常モード: manualRows を送る
 *  - ドスコイ: getManualDiscounts() を rows 化して送る
 *  - ルール選択がある場合は discount_rule（id）も添付
 * --------------------------------------------------------- */
function buildManualRowsPayload() {
  // 通常モードの手入力行をAPI向け形式に正規化(そのまま1行として保存)
  const rows = (manualRows.value || [])
    .map((r, i) => ({
      label: String(r.label || '').trim(),
      amount: Number(r.amount || 0),
      sort_order: i,
    }))
    .filter(r => r.label && r.amount > 0)
  return rows
}

function buildDosukoiRowsPayload() {
  // ステップ割引を個別行に展開(×3 → 3行)
  const rows = []
  stepRules.value.forEach((rule, ruleIdx) => {
    const qty = Number(dosukoiQtyMap.value[rule.id] || 0)
    const unitAmount = Number(rule.amount_off || 0)
    if (qty <= 0 || unitAmount <= 0) return
    
    const ruleName = rule.name || `¥${unitAmount.toLocaleString()}`
    for (let i = 0; i < qty; i++) {
      rows.push({
        label: ruleName,
        amount: unitAmount,
        sort_order: rows.length,
      })
    }
  })
  return rows
}

function onSaveDiscount() {
  // 新規入力分を取得
  const newRows = isDosukoiMode.value
    ? buildDosukoiRowsPayload()
    : buildManualRowsPayload()
  
  if (!newRows.length) return
  
  // 保存済み + 新規を結合
  const allRows = [
    ...savedDiscountRows.value.map(r => ({ label: r.label, amount: r.amount })),
    ...newRows
  ].map((r, i) => ({ ...r, sort_order: i }))
  
  const discount_rule = (selectedDiscountId.value == null) ? null : Number(selectedDiscountId.value)
  const payload = { manual_discounts: allRows, discount_rule }
  
  // 即座にローカルの保存済みリストを更新（alert前に反映）
  savedDiscountRows.value = allRows.map((r, i) => ({
    id: `saved-${Date.now()}-${i}`,
    label: r.label,
    amount: r.amount,
  }))
  
  // 保存後、新規入力をリセット
  if (isDosukoiMode.value) {
    Object.keys(dosukoiQtyMap.value).forEach(k => { dosukoiQtyMap.value[k] = 0 })
  } else {
    manualRows.value = [{ label: '', amount: 0 }]
  }
  
  // サーバへ保存
  emit('saveDiscount', payload)
}

// 保存済み割引の個別削除
function removeSavedDiscount(index) {
  // 即座にローカルから削除
  savedDiscountRows.value.splice(index, 1)
  
  // サーバに反映
  const allRows = savedDiscountRows.value.map((r, i) => ({
    label: r.label,
    amount: r.amount,
    sort_order: i
  }))
  const discount_rule = (selectedDiscountId.value == null) ? null : Number(selectedDiscountId.value)
  
  // 削除は即座に反映済みなので、サーバへ送信（alertなし）
  emit('saveDiscount', { manual_discounts: allRows, discount_rule })
}
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


    <!-- 割引(通常:手入力) -->
    <div class="coupon" v-if="!isDosukoiMode">
      <!-- ヘッダ:クリックで開閉 -->
      <label
        class="form-label fw-bold d-flex align-items-center justify-content-between w-100 bg-light p-2 rounded"
        role="button"
        :aria-expanded="showDiscountPanel"
        @click="toggleDiscountPanel"
      >
        割引
        <IconChevronUp :class="{'rotate-180': showDiscountPanel}" :size="20" />
      </label>

      <!-- 本体 -->
      <div class="wrap collapse-body mt-2" v-show="showDiscountPanel">
        <!-- 保存済み割引リスト -->
        <div v-if="savedDiscountRows.length" class="saved-discounts mb-3 p-2 bg-success bg-opacity-10 rounded">
          <div class="small fw-bold text-success mb-2">保存済み割引</div>
          
          <div class="d-flex flex-column gap-1">
            <div
              v-for="(row, i) in savedDiscountRows"
              :key="row.id"
              class="d-flex align-items-center justify-content-between bg-white rounded px-2 py-1"
            >
              <span class="small">{{ row.label }}</span>
              <div class="d-flex align-items-center gap-2">
                <span class="small fw-bold">¥{{ row.amount.toLocaleString() }}</span>
                <button type="button" class="btn btn-sm btn-link text-danger p-0" @click="removeSavedDiscount(i)">
                  <IconX :size="16" />
                </button>
              </div>
            </div>
          </div>
          <div class="small text-end mt-2">
            保存済み合計: <strong>¥{{ savedDiscountAmount.toLocaleString() }}</strong>
          </div>
        </div>

        <!-- 新規入力 -->
        <div class="new-input-section">
          <div class="small fw-bold mb-2">新規入力</div>
        <!-- 行リスト -->
        <div class="d-flex flex-column gap-2">
          <div
            v-for="(row,i) in manualRows"
            :key="i"
            class="row g-2 align-items-center"
          >
            <!-- 明細 -->
            <div class="col-8">
              <input
                class="form-control meisai"
                type="text"
                v-model="row.label"
                placeholder="割引明細（例：クーポン／紹介）"
              />
            </div>

            <!-- 金額 -->
            <div class="col-4">
              <div class="input-group d-flex align-items-center gap-1">
                <span>¥</span>
                <input
                  class="form-control"
                  type="number"
                  min="0"
                  step="1"
                  v-model.number="row.amount"
                  placeholder="金額"
                />
              </div>
            </div>
              <!-- <button
                type="button"
                class="btn btn-outline-danger"
                @click="removeManualRow(i)"
                aria-label="この割引行を削除"
              >
                <IconTrash :size="16" />
              </button> -->
          </div>
        </div>

        <!-- 追加 & 合計 -->
        <div class="d-flex align-items-center justify-content-between mt-2">
          <div class="wrap">
            <button type="button" class="btn text-danger p-1" @click="removeManualRow(i)" aria-label="この割引行を削除" >
              <IconCircleDashedX style="width: 24px;" />
            </button>
            <button type="button" class="btn text-success p-1" @click="addManualRow">
              <IconCircleDashedPlus style="width: 24px;"/>
            </button>
          </div>

          <div class="small text-end">
            合計割引:
            <strong>¥{{ manualDiscountAmount.toLocaleString() }}</strong>
          </div>
        </div>
        </div>
      </div>
      <button class="btn btn-secondary mt-2" type="button"
          :disabled="manualDiscountAmount<=0"
          @click="onSaveDiscount">
        割引を保存
      </button>
    </div>



    <!-- 割引(dosukoi-asa 専用:金額 -0+) -->
    <div class="coupon coupon--dosukoi" v-else>
      <label
        class="form-label fw-bold d-flex align-items-center justify-content-between w-100 bg-light p-2"
        role="button"
        :aria-expanded="showDiscountPanel"
        @click="toggleDiscountPanel"
      >
        割引
        <IconChevronUp :class="{'rotate-180': showDiscountPanel}" :size="24" />
      </label>
      <div
        class="wrap p-2 collapse-body"
        v-show="showDiscountPanel"
      >
        <!-- 保存済み割引リスト -->
        <div v-if="savedDiscountRows.length" class="saved-discounts mb-3 p-2 bg-success bg-opacity-10 rounded">
          <div class="small fw-bold text-success mb-2">保存済み割引</div>

          <div class="row g-2">
            <div
              v-for="(row, i) in savedDiscountRows"
              :key="row.id"
              class="col-6"
            >
              <div class="d-flex align-items-center justify-content-between bg-white rounded p-1">
                <div class="wrap df-center w-100 gap-2">
                  <!-- <span class="small">{{ row.label }}</span> -->
                  <span class="small fw-bold">-¥{{ row.amount.toLocaleString() }}</span>
                </div>
                <button type="button" class="btn btn-sm btn-link text-danger p-0" @click="removeSavedDiscount(i)">
                  <IconX :size="14" />
                </button>
              </div>
            </div>
          </div>

          <div class="small text-end mt-2">
            保存済み合計: <strong>¥{{ savedDiscountAmount.toLocaleString() }}</strong>
          </div>
        </div>

        <!-- 新規入力: ステップの並び -->
        <div class="d-flex flex-wrap gap-2">
          <div
            v-for="r in stepRules"
            :key="r.id"
            class="d-inline-flex align-items-center bg-white border rounded-pill px-2 py-1"
            style="min-width: 140px;"
          >
            <button type="button" class="btn btn-link p-0 me-2" @click="decStep(r.id)">
              <IconMinus :size="16" />
            </button>
            <span class="me-2">¥{{ Number(r.amount_off).toLocaleString() }}</span>
            <span class="badge bg-secondary me-2">{{ dosukoiQtyMap[r.id] || 0 }}</span>
            <button type="button" class="btn btn-link p-0" @click="incStep(r.id)">
              <IconPlus :size="16" />
            </button>
          </div>
          <span v-if="!stepRules.length" class="text-muted small">
            （管理画面に「Payで表示」の金額割引がありません）
          </span>
        </div>

        <!-- 新規入力の合計 -->
        <div class="mt-4 small text-end">
          新規入力: <strong>¥{{ dosukoiDiscountAmount.toLocaleString() }}</strong>
        </div>
        <!-- 保存ボタン -->
        <button class="btn btn-sm w-100 btn-secondary mt-2" type="button"
                :disabled="dosukoiDiscountAmount<=0"
                @click="onSaveDiscount">
          割引を保存
        </button>

      </div>

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



<style scoped lang="scss">

.collapse-body {
  transition: all .5s ease;
}
.rotate-180 {
  transform: rotate(180deg);
  transition: transform .5s ease;
}

/* ▼ placeholder サイズだけ上書き */
.form-control.meisai::placeholder { font-size: .8rem !important; }
/* Safari/Chrome など */
.form-control.meisai::-webkit-input-placeholder { font-size: .8rem !important; }
/* Firefox */
.form-control.meisai::-moz-placeholder          { font-size: .8rem !important; }

</style>