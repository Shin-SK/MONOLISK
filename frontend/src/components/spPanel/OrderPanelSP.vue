<script setup>
import { reactive, computed, ref, nextTick, onUnmounted } from 'vue'

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


const props = defineProps({
  catOptions:        { type: Array,  default: () => [] }, // [{value,label}]
  selectedCat:       { type: [String, null], default: null },
  orderMasters:      { type: Array,  default: () => [] }, // [{id,name}]
  servedByOptions:   { type: Array,  default: () => [] }, // [{id,label}]
  servedByCastId:  { type: [Number, String], default: null },
  /* ▼ 追加：pending を受けて“選択済み表示”に使う */
  pending:           { type: Array,  default: () => [] }, // [{master_id, qty, cast_id}]
  masterNameMap:     { type: Object, default: () => ({}) },
  servedByMap:       { type: Object, default: () => ({}) },
  masterPriceMap:  { type: Object, default: () => ({}) },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:selectedCat', 'update:servedByCastId',
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

/*  各アイテムの数量（ローカル） */
const qtyMap = reactive({})                 // { [masterId]: qty }
const keyOf  = (id) => String(id)
const qtyOf  = (id) => qtyMap[keyOf(id)] ?? 0    // ★ 初期値を0に
const inc    = (id) => qtyMap[keyOf(id)] = qtyOf(id) + 1
const dec    = (id) => qtyMap[keyOf(id)] = Math.max(0, qtyOf(id) - 1)  // ★ 0未満にしない
const add    = (id) => {
	const k = keyOf(id)
	const q = qtyOf(id)
	if (q <= 0) return            // ★ 0個のまま「◯+」なら何もしない（←運用に合わせて）
	emit('addPending', id, q)
	qtyMap[k] = 0                 // ★ 追加後は0にリセット
	pokeCartFeedback()
}

//  親から誤って Ref のまま来ても配列に正規化する保険
const listServedBy = computed(() => {
  const v = props.servedByOptions
  // 配列ならそのまま、Ref/Computed なら .value、その他は空配列
  return Array.isArray(v) ? v : (Array.isArray(v?.value) ? v.value : [])
})
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
    <div class="wrap">
      <!-- 横スクロールのカテゴリタブ -->
      <div class="order-tabs" tabindex="-1">
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
      <div class="served-by mt-3">
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
      </div>

      <!-- 品目リスト（タップで pending へ） -->
      <div class="order-list d-flex flex-column my-5 gap-2">
        <div
          v-for="m in orderMasters"
          :key="m.id"
          class="d-flex justify-content-between p-2 bg-light"
        >
          <!-- 左：アイテム情報 -->
          <div class="item-area d-flex gap-2 ms-2">
            <div class="d-flex flex-column flex-wrap justify-content-center">
              <div class="name fs-md-5 fw-bold">{{ m.name }}</div>
              <div class="price" v-if="m.price != null">¥{{ Number(m.price).toLocaleString() }}</div>
            </div>
          </div>

          <!-- 右：数量ステッパー & 追加 -->
          <div class="d-flex align-items-center">
            <!-- 数量ステッパー -->
            <div class="cartbutton d-flex align-items-center">
              <div class="d-flex align-items-center gap-3 bg-white h-auto p-2 m-2" style="border-radius:100px;">
                <button
                  type="button"
                  @click="dec(m.id)"
                  :class="{ invisible: qtyOf(m.id) === 0 }"
                >
                  <IconMinus :size="16" />
                </button>
                <span>{{ qtyOf(m.id) }}</span>
                <button type="button" @click="inc(m.id)"><IconPlus :size="16" /></button>
              </div>
            </div>
            <div class="addbutton d-flex align-items-center">
              <button type="button" @click="add(m.id)"><IconCirclePlus /></button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 下部カート（最小版） -->
    <div v-if="pending && pending.length" ref="cartEl" class="cart mt-5" :class="{ pulse: cartPulse }">

      <div class="cart-items">
        <div v-for="(p,i) in pending" :key="i" class="cart-item d-flex justify-content-between align-items-center">

          <div class="wrap">
            <div v-if="p.cast_id" class="badge bg-secondary">
              {{ servedByMap[String(p.cast_id)] || ('cast#' + p.cast_id) }}
            </div>
            <div class="d-flex align-items-center gap-2">
              <div class="name fs-md-5 fw-bold">
              {{ masterNameMap[String(p.master_id)]
                || (orderMasters.find(x => x.id === p.master_id)?.name)
                || ('#' + p.master_id) }}
              </div>
            </div>
            <div class="d-flex align-items-center gap-2">
              <div class="price" v-if="props.masterPriceMap[String(p.master_id)] != null">
                ¥{{ Number(props.masterPriceMap[String(p.master_id)]).toLocaleString() }}
              </div>
              <div class="qty">
                <IconX :size="8"/>{{ p.qty }}
              </div>
            </div>
          </div>

          <button type="button" class="del" @click="emit('removePending', i)">×</button>
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

.invisible {
  visibility: hidden;
  width: 0px;
  padding: 0px 4px;
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
