<script setup>
import { reactive, computed, ref, nextTick, onUnmounted, watch } from 'vue'

const cartEl     = ref(null)   // カートDOM
const showJump   = ref(false)  // 「カートを見る」ボタン表示
const cartPulse  = ref(false)  // カートの強調アニメ
let hideTimer    = null
const PERSIST_JUMP = false //デザインチェック

function jumpToCart () {
  if (!PERSIST_JUMP) showJump.value = false
  nextTick(() => cartEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

function pokeCartFeedback () {
  showJump.value = true
  clearTimeout(hideTimer)
  if (!PERSIST_JUMP) {
    hideTimer = setTimeout(() => (showJump.value = false), 3500)
  }
  cartPulse.value = true
  setTimeout(() => (cartPulse.value = false), 1200)
}

onUnmounted(() => clearTimeout(hideTimer))

function ensurePendingCastIds() {
  const list = servedByOptions.value || []
  const fallbackId = (ed.servedByCastId?.value != null)
    ? Number(ed.servedByCastId.value)
    : (list.length ? Number(list[0].id) : null)

  if (!fallbackId || !Array.isArray(ed.pending?.value)) return

  for (const p of ed.pending.value) {
    if (p && (p.cast_id == null || p.cast_id === '')) {
      p.cast_id = fallbackId
    }
  }
}

const props = defineProps({
  catOptions:        { type: Array,  default: () => [] }, // [{value,label}]
  selectedCat:       { type: [String, null], default: null },
  orderMasters:      { type: Array,  default: () => [] }, // [{id,name}]
  servedByOptions:   { type: Array,  default: () => [] }, // [{id,label}]
  servedByCastId:  { type: [Number, String], default: null },
  servedByCastIds: { type: Array, default: () => [] },
  /* ▼ 追加：pending を受けて“選択済み表示”に使う */
  pending:           { type: Array,  default: () => [] }, // [{master_id, qty, cast_id, customer_id}]
  masterNameMap:     { type: Object, default: () => ({}) },
  servedByMap:       { type: Object, default: () => ({}) },
  masterPriceMap:  { type: Object, default: () => ({}) },
  billCustomers:     { type: Array,  default: () => [] }, // 本指名顧客一覧
  selectedCustomerId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:selectedCat', 'update:servedByCastId', 'update:servedByCastIds', 'update:selectedCustomerId',
  'addPending', 'removePending', 'clearPending',
  'placeOrder'
])

/* 提供者 */
const onServedChange = (e) => {
  const v = e.target.value
  emit('update:servedByCastId', v === '' ? null : Number(v))
}

/* 選択ハイライト：pending に同じ master_id があれば active */
const isActive = (masterId) => props.pending?.some?.(p => p && p.master_id === masterId)

//  親から誤って Ref のまま来ても配列に正規化する保険
const listServedBy = computed(() => {
  const v = props.servedByOptions
  // 配列ならそのまま、Ref/Computed なら .value、その他は空配列
  return Array.isArray(v) ? v : (Array.isArray(v?.value) ? v.value : [])
})

function defaultCastId () {
  // 1) すでに上で選ばれているならそれ
  if (props.servedByCastId != null) return Number(props.servedByCastId)

  // 2) 選択肢の先頭（=「とりあえず誰か」）
  const list = listServedBy.value || []
  if (list.length) return Number(list[0].id)

  // 3) 本当に誰もいない（卓にキャストがいない等）
  return null
}

const normalizeIds = (v) => {
  const src = Array.isArray(v) ? v : []
  const out = []
  for (const x of src) {
    const n = Number(x)
    if (!Number.isFinite(n)) continue
    if (!out.includes(n)) out.push(n)
  }
  return out
}

/* ▼ 選択中（詳細カードを開いている）アイテム */
const activeMasterId = ref(null)     // 今開いてる master_id
const activeQty      = ref(1)        // 詳細カード内の数量
const activeCastIds  = ref(normalizeIds(props.servedByCastIds))
const activeCustomerId = ref(null)   // 詳細カード内の顧客（一時選択）

function openDetail(masterId) {
  // 同じのを押したら閉じる
  if (activeMasterId.value === masterId) {
    activeMasterId.value = null
    return
  }
  activeMasterId.value = masterId
  activeQty.value = 1
  activeCastIds.value = normalizeIds(props.servedByCastIds)

  // 顧客をデフォルトで最初の顧客に設定
  const firstCustomer = (props.billCustomers && props.billCustomers.length) ? props.billCustomers[0].customer_id : null
  activeCustomerId.value = firstCustomer
  emit('update:selectedCustomerId', firstCustomer)

  // 開いた直後に見切れないように微スクロールしたいならここに nextTick で処理も可
}

/**
 * ★ここが肝：
 * 詳細が開いてる & activeCastId が無効（null/存在しない）& servedByOptions が後から入ってきた
 * → 先頭を自動で選ぶ（必ず誰か決まっている状態を保証）
 */
watch(
  () => listServedBy.value,
  (list) => {
    if (activeMasterId.value == null) return
    const ids = new Set((list || []).map(x => Number(x.id)))
    activeCastIds.value = normalizeIds(activeCastIds.value).filter(id => ids.has(id))
  },
  { immediate: true }
)

watch(
  () => props.servedByCastIds,
  (ids) => {
    if (activeMasterId.value == null) {
      activeCastIds.value = normalizeIds(ids)
    }
  },
  { deep: true }
)

function toggleActiveCast(castId) {
  const id = Number(castId)
  if (!Number.isFinite(id)) return
  const next = normalizeIds(activeCastIds.value)
  const idx = next.indexOf(id)
  if (idx >= 0) next.splice(idx, 1)
  else next.push(id)
  activeCastIds.value = next
}

function clearActiveCasts() {
  activeCastIds.value = []
}

function incActive() { activeQty.value = Math.max(1, Number(activeQty.value || 1) + 1) }
function decActive() { activeQty.value = Math.max(1, Number(activeQty.value || 1) - 1) }

function confirmAdd(masterId) {
  const q = Math.max(1, Number(activeQty.value || 1))
  const ids = normalizeIds(activeCastIds.value)

  emit('update:servedByCastIds', ids)
  emit('update:servedByCastId', ids.length ? ids[0] : null)

  // 【フェーズ3】顧客IDも一緒に送信（親側で customer_id として保持される）
  emit('addPending', masterId, q, ids, activeCustomerId.value)

  activeMasterId.value = null
  pokeCartFeedback()
}

const k = (v) => (v == null ? '' : String(v))

const yen = (n) => `¥${(Number(n) || 0).toLocaleString()}`

// 【フェーズ3】顧客ID → 表示名のマップ
const billCustomersMap = computed(() => {
  const map = {}
  for (const bc of (props.billCustomers || [])) {
    if (bc && bc.customer_id) {
      map[String(bc.customer_id)] = bc.display_name || bc.customer_name || `Guest-${String(bc.customer_id).padStart(6, '0')}`
    }
  }
  return map
})

const priceOf = (id) => {
  const key = String(id)
  const mp  = props.masterPriceMap?.[key]
  if (mp != null) return Number(mp) || 0
  const found = props.orderMasters?.find?.(x => x && x.id === id)
  return Number(found?.price) || 0
}

const cartSubtotal = computed(() =>
  (props.pending || []).reduce((s, p) =>
    s + priceOf(p.master_id) * (Number(p.qty) || 0), 0)
)

function castNamesFromPending(p) {
  const ids = Array.isArray(p?.cast_ids)
    ? normalizeIds(p.cast_ids)
    : (p?.cast_id != null ? [Number(p.cast_id)] : [])
  return ids
    .map(id => props.servedByMap[String(id)] || ('cast#' + id))
    .filter(Boolean)
    .join('＋')
}

</script>

<template>
  <div class="panel order">

    <div class="wrap d-flex flex-column flex-grow-1 min-h-0 overflow-hidden">
      <!-- 横スクロールのカテゴリタブ -->
      <div class="order-tabs flex-shrink-0" tabindex="-1">
        <button
          v-for="o in catOptions"
          :key="o.value"
          type="button"
          class="tab"
          :class="{ active: selectedCat === o.value }"
          @click="emit('update:selectedCat', o.value)"
        >
          {{ o.label }}
        </button>
      </div>

      <!-- 品目リスト（タップで pending へ） -->
      <div
        class="order-list d-flex flex-column gap-2 flex-grow-1 min-h-0 mt-3"
        style="overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch;"
        >
        <div
          v-for="m in orderMasters"
          :key="m.id"
          class="d-flex flex-column gap-2"
        >
          <button type="button" class="btn p-0" @click="openDetail(m.id)">
            <!-- 行（タップで詳細を開く） -->
            <div class="d-flex justify-content-between p-2 bg-light">
              <!-- 左：アイテム情報 -->
              <div class="item-area d-flex gap-2 ms-2">
                <div class="d-flex flex-column flex-wrap justify-content-center align-items-start">
                  <div class="name fs-md-5 fw-bold">{{ m.name }}</div>
                </div>
              </div>

              <!-- 右：＋だけ（選択） -->
              <div class="d-flex align-items-center me-2">
                  <div class="price me-2" v-if="m.price != null">¥{{ Number(m.price).toLocaleString() }}</div>
                  <IconCirclePlus />
              </div>
            </div>
          </button>
          <!-- 詳細カード（このメニューを選んだ時だけ出る） -->
          <div v-if="activeMasterId === m.id" class="detail-card bg-white border rounded p-3 mx-2">
            <div class="fw-bold mb-2 d-flex align-items-center justify-content-between">
              {{ m.name }} <span class="text-muted ms-2" v-if="m.price != null">¥{{ Number(m.price).toLocaleString() }}</span>
            </div>
            <div class="d-flex align-items-center justify-content-between mb-3">
              <div class="text-muted small fw-bold text-nowrap">担当</div>
              <div class="served-pills flex-wrap" role="tablist">
                <button
                  type="button"
                  class="badge bg-light text-secondary rounded-pill"
                  :class="{ active: !activeCastIds.length }"
                  :aria-pressed="!activeCastIds.length"
                  @click="clearActiveCasts"
                  style="font-size: 1rem;"
                >未指定</button>
                <template v-if="listServedBy.length">
                  <button
                    v-for="c in listServedBy"
                    :key="String(c.id)"
                    type="button"
                    class="badge bg-light text-secondary rounded-pill"
                    :class="{ active: activeCastIds.includes(Number(c.id)) }"
                    :aria-pressed="activeCastIds.includes(Number(c.id))"
                    @click="() => toggleActiveCast(c.id)"
                    style="font-size: 1rem;"
                  >{{ c.label }}</button>
                </template>
                <div v-else class="text-danger small">
                  担当できるキャストがいません（先にキャストを着席させてください）
                </div>
              </div>
            </div>

            <!-- 顧客選択（オプション） -->
            <div class="d-flex align-items-center justify-content-between mb-3">
              <label class="text-muted small fw-bold text-nowrap">顧客</label>
              <div class="served-pills flex-wrap" role="tablist">
                <button
                  type="button"
                  class="badge bg-light text-secondary rounded-pill"
                  :class="{ active: activeCustomerId == null }"
                  :aria-pressed="activeCustomerId == null"
                  @click="() => { activeCustomerId = null; emit('update:selectedCustomerId', null) }"
                  style="font-size: 1rem;"
                >未指定</button>

                <button
                  v-for="bc in billCustomers"
                  :key="bc.id"
                  type="button"
                  class="badge bg-light text-secondary rounded-pill"
                  :class="{ active: activeCustomerId === bc.customer_id }"
                  :aria-pressed="activeCustomerId === bc.customer_id"
                  @click="() => { activeCustomerId = bc.customer_id; emit('update:selectedCustomerId', bc.customer_id) }"
                  style="font-size: 1rem;"
                >{{ bc.display_name }}</button>
              </div>
            </div>
            <div class="d-flex align-items-center justify-content-between mb-3 gap-2">
              <div class="text-muted small fw-bold">数</div>
              <div class="d-flex align-items-center gap-3 bg-light p-2 flex-wrap" style="border-radius:999px;">
                <button type="button" class="btn btn-link p-0" @click="decActive"><IconMinus :size="16" /></button>
                <span style="min-width: 2ch; text-align:center;">{{ activeQty }}</span>
                <button type="button" class="btn btn-link p-0" @click="incActive"><IconPlus :size="16" /></button>
              </div>
            </div>



            <button type="button" class="btn btn-sm btn-warning w-100" @click="confirmAdd(m.id)">
              追加
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 下部カート（最小版） -->
    <div v-if="pending && pending.length" ref="cartEl" class="cart mt-5 flex-shrink-0 border p-2 rounded" :class="{ pulse: cartPulse }">
      <div class="cart-header mb-3">
        <div class="df-center w-100 py-1 fw-bold gap-2">
          <IconGardenCart />注文カート
        </div>

      </div>
      <div class="cart-items">
        <div v-for="(p,i) in pending" :key="i" class="cart-item d-flex justify-content-between align-items-center p-2 bg-light mb-2">

          <div class="df-center gap-2">
            <button type="button" class="p-0" @click="emit('removePending', i)"><IconX :size="8" class="small"/></button>
            <div class="box">
              <div class="name fs-md-5 fw-bold">
              {{ masterNameMap[String(p.master_id)]
                || (orderMasters.find(x => x.id === p.master_id)?.name)
                || ('#' + p.master_id) }}
              </div>
              <div class="d-flex gap-2 flex-wrap mt-1">
                <div v-if="castNamesFromPending(p)" class="badge bg-secondary">
                  {{ castNamesFromPending(p) }}
                  <template v-if="p.customer_id != null && p.customer_id !== ''">
                    / {{ billCustomersMap[String(p.customer_id)] || ('Guest-' + String(p.customer_id).padStart(6, '0')) }}
                  </template>
                </div>
              </div>
            </div>

          </div>

          <div class="d-flex align-items-center justify-content-end gap-3">
            <div class="df-center gap-2">
              <div class="price" v-if="props.masterPriceMap[String(p.master_id)] != null">
                ¥{{ Number(props.masterPriceMap[String(p.master_id)]).toLocaleString() }}
              </div>
              <div class="qty">
                ×{{ p.qty }}
              </div>
            </div>
          </div>

        </div>
      </div>

      <div class="subtotal fw-bold d-flex align-items-center justify-content-between py-3">
        <span>小計</span>
        <span>{{ yen(cartSubtotal) }}</span>
      </div>

      <div class="orderbutton mt-5 d-flex flex-column justify-content-center">
        <!-- 仮会計では注文ボタンを隠す -->
        <button v-if="!props.readonly" class="btn btn-warning w-100" @click="$emit('placeOrder')">注文</button>
        <button type="button" class="clear btn btn-sm mt-2" @click="emit('clearPending')">クリア</button>
        <small class="mt-5 text-muted df-center">
          修正は会計パネルから行ってください。
        </small>
      </div>
    </div>
    <!-- カートへ移動ボタン（フェード IN/OUT） -->
    <Transition name="fade" appear>
      <button
        v-if="showJump"
        type="button"
        class="jump-toast btn btn-warning rounded-circle p-3"
        @click="jumpToCart"
      >
        <IconChevronDown :size="18" />
      </button>
    </Transition>
  </div>
</template>

<style scoped>
.panel.order {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel.order .wrap {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.panel.order .order-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
}

.invisible {
  visibility: hidden;
  width: 0px;
  padding: 0px 4px;
}

.detail-card {
  box-shadow: 0 6px 16px rgba(0,0,0,.06);
}

/* 担当選択badge */
.badge.active {
  background-color: #212529 !important;
  color: #fff !important;
  font-weight: 600;
}

/* 浮遊ボタン */
.jump-toast{
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 160px;      /* フッターがあれば余裕を取る */
  z-index: 1100;
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  box-shadow: 0 8px 20px rgba(0,0,0,.25);
  border: 0;
  cursor: pointer;
  aspect-ratio: 1/1;
}

/* カート強調（2回点滅） */
.cart {
  border-color: #ccc !important;
}

@keyframes pulseGlow {
  0%   { box-shadow: 0 0 0 0 rgba(255,193,7,.55); }
  100% { box-shadow: 0 0 0 18px rgba(255,193,7,0); }
}
.cart.pulse{
  animation: pulseGlow 0.6s ease-out 2;
  border-radius: 12px;
}

/* IN/OUT の共通トランジション */
.fade-enter-active,
.fade-leave-active {
  transition: opacity .25s ease, transform .25s ease;
}

/* IN の開始 / OUT の終了  */
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 8px) scale(.95);
}

</style>
