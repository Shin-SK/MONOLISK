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
  'update:selectedCat', 'update:servedByCastId', 'update:selectedCustomerId',
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

/* ▼ 選択中（詳細カードを開いている）アイテム */
const activeMasterId = ref(null)     // 今開いてる master_id
const activeQty      = ref(1)        // 詳細カード内の数量
const activeCastId   = ref(null)     // 詳細カード内の担当（null=未指定）
const castTouched    = ref(false)    // ユーザーが担当を操作したか

function openDetail(masterId) {
  // 同じのを押したら閉じる
  if (activeMasterId.value === masterId) {
    activeMasterId.value = null
    return
  }
  activeMasterId.value = masterId
  activeQty.value = 1
  castTouched.value = false
  // 必ず担当を初期選択
  activeCastId.value = defaultCastId()

  // 開いた直後に見切れないように微スクロールしたいならここに nextTick で処理も可
}

/**
 * ★ここが肝：
 * 詳細が開いてる & activeCastId が null のまま & servedByOptions が後から入ってきた
 * → 先頭を自動で選ぶ（ただしユーザーが操作済みなら上書きしない）
 */
watch(
  () => listServedBy.value,
  (list) => {
    if (activeMasterId.value == null) return
    if (castTouched.value) return          // ← ここが肝：ユーザー操作後は自動上書きしない
    if (activeCastId.value != null) return
    if ((list?.length || 0) === 0) return
    activeCastId.value = Number(list[0].id)
  },
   { immediate: true }
)

function incActive() { activeQty.value = Math.max(1, Number(activeQty.value || 1) + 1) }
function decActive() { activeQty.value = Math.max(1, Number(activeQty.value || 1) - 1) }

function confirmAdd(masterId) {
  const q = Math.max(1, Number(activeQty.value || 1))

  // ★ 最終ガード：未選択なら自動で先頭キャスト
  const ensured = (activeCastId.value == null) ? defaultCastId() : Number(activeCastId.value)
  if (ensured == null) {
    alert('担当できるキャストがいません（先にキャストを着席させてください）')
    return
  }

  // ★ 親が cast_id を受け取れるように addPending を拡張する前提
  //  (現状 emit('addPending', id, q) なので、親も 3引数対応にする)
  emit('addPending', masterId, q, ensured)

  activeMasterId.value = null
  pokeCartFeedback()
}

const k = (v) => (v == null ? '' : String(v))

const yen = (n) => `¥${(Number(n) || 0).toLocaleString()}`

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

      <!-- 提供者（今ついてる卓の人だけ／未指定含む） -->
      <!-- <div class="served-by mt-3 flex-shrink-0">
        <label class="served-label"><IconUser /></label>
        <div class="served-pills" role="tablist">
          <button
            type="button"
            class="pill"
            :class="{ active: servedByCastId == null }"
            :aria-pressed="servedByCastId == null"
            @click="emit('update:servedByCastId', null)"
          >未指定</button>

          <button
            v-for="c in listServedBy"
            :key="String(c.id)"
            type="button"
            class="pill"
            :class="{ active: k(servedByCastId) === k(c.id) }"
            :aria-pressed="k(servedByCastId) === k(c.id)"
            @click="emit('update:servedByCastId', c.id)"
          >{{ c.label }}</button>
        </div>
      </div> -->

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
                  :class="{ active: activeCastId == null }"
                  :aria-pressed="activeCastId == null"
                  @click="() => { castTouched = true; activeCastId = null }"
                  style="font-size: 1rem;"
                >未選択</button>

                <button
                  v-for="c in listServedBy"
                  :key="String(c.id)"
                  type="button"
                  class="badge bg-light text-secondary rounded-pill"
                  :class="{ active: k(activeCastId) === k(c.id) }"
                  :aria-pressed="k(activeCastId) === k(c.id)"
                  @click="() => { castTouched = true; activeCastId = Number(c.id) }"
                  style="font-size: 1rem;"
                >{{ c.label }}</button>
              </div>
            </div>

            <!-- 顧客選択（オプション） -->
            <div class="d-flex align-items-center justify-content-between mb-3 gap-2">
              <label class="text-muted small fw-bold" style="min-width: 60px">顧客</label>
              <select 
                class="form-select form-select-sm" 
                :value="selectedCustomerId"
                @change="e => emit('update:selectedCustomerId', e.target.value ? Number(e.target.value) : null)"
              >
                <option :value="null">未指定</option>
                <option v-for="bc in billCustomers" :key="bc.id" :value="bc.customer_id">
                  {{ bc.display_name }}
                </option>
              </select>
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
              <div v-if="p.cast_id" class="badge bg-secondary">
                {{ servedByMap[String(p.cast_id)] || ('cast#' + p.cast_id) }}
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
