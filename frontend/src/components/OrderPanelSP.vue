<script setup>
import { reactive, computed } from 'vue'

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
const qtyOf  = (id) => qtyMap[keyOf(id)] ?? 1
const inc    = (id) => qtyMap[keyOf(id)] = qtyOf(id) + 1
const dec    = (id) => qtyMap[keyOf(id)] = Math.max(1, qtyOf(id) - 1)
const add    = (id) => {
  const k = keyOf(id)
  const q = qtyOf(id)
  emit('addPending', id, q)
  qtyMap[k] = 1
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
      <div class="order-list d-grid my-5 gap-2">
        <div
          v-for="m in orderMasters"
          :key="m.id"
          class="card d-flex flex-row justify-content-between p-2"
        >
          <!-- 左：アイテム情報 -->
          <div class="item-area d-flex gap-2 ms-2">
            <div class="d-flex flex-column flex-wrap justify-content-center">
              <div class="name fs-5 fw-bold">{{ m.name }}</div>
              <div class="price" v-if="m.price != null">¥{{ Number(m.price).toLocaleString() }}</div>
            </div>
          </div>

          <!-- 右：数量ステッパー & 追加 -->
          <div class="d-flex align-items-center">
            <!-- 数量ステッパー -->
            <div class="cartbutton d-flex align-items-center">
              <div class="d-flex align-items-center gap-3 bg-white h-auto p-2 m-2" style="border-radius:100px;">
                <button type="button" @click="dec(m.id)"><IconMinus :size="16" /></button>
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
    <div v-if="pending && pending.length" class="cart mt-5">

      <div class="cart-items">
        <div v-for="(p,i) in pending" :key="i" class="cart-item d-flex justify-content-between align-items-center">

          <div class="wrap">
            <div v-if="p.cast_id" class="badge bg-secondary">
              {{ servedByMap[String(p.cast_id)] || ('cast#' + p.cast_id) }}
            </div>
            <div class="d-flex align-items-center gap-2">
              <div class="name fs-5 fw-bold">
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
        <button class="btn btn-warning w-100" @click="$emit('placeOrder')">注文</button>
        <button type="button" class="clear btn btn-sm" @click="emit('clearPending')">クリア</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 必要ならここに追加のスタイルを */
</style>
