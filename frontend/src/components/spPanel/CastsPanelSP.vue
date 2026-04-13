<!-- CastsPanelSP.vue（差し替え） -->
<script setup>
import { ref, computed } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'

const props = defineProps({
  currentCasts: { type: Array,  default: () => [] },
  benchCasts:   { type: Array,  default: () => [] },
  onDutyIds:    { type: Array,  default: () => [] },
  keyword:      { type: String, default: '' },
  billId: { type: [Number, null], default: null },
  billCustomers: { type: Array, default: () => [] },
})
// 同伴イベントを追加 + setMainWithCustomer を追加
const emit = defineEmits(['update:keyword','setFree','setInhouse','setMain','setDohan','setHelp','removeCast','save','setMainWithCustomer'])

const isOnDuty = (c) => Array.isArray(props.onDutyIds) && props.onDutyIds.includes(Number(c?.id))

const safeCurrent = computed(() =>
  Array.isArray(props.currentCasts) ? props.currentCasts.filter(c => c && c.id != null) : []
)
const safeBench = computed(() =>
  (Array.isArray(props.benchCasts) ? props.benchCasts : [])
    .filter(c => c && c.id != null)
    .filter(isOnDuty)
)

/* 色クラス（堅牢版）
   優先: stay_type → role/dohan/inhouse → is_honshimei/is_main
   'nom'   = 本指（赤）
   'dohan' = 同伴（グレー/黄）
   'in'    = 場内（緑）
   それ以外 = フリー（青）
*/
const tagClass = (c) => {
  // help は free 上のフラグ。見た目は“紫”を最優先で反映
  if (c?.is_help === true) return 'bg-purple text-white'
  // 1) stay_type が来ていればそれで確定
  let st = c?.stay_type
  // 2) 互換: role/dohan/inhouse から推定
  if (!st) {
    if (c?.role === 'main') st = 'nom'
    else if (c?.dohan)      st = 'dohan'
    else if (c?.inhouse)    st = 'in'
    else if (c?.is_help)    st = 'help'
  }
  // 3) さらに互換: is_honshimei / is_main 系
  if (!st) {
    if (c?.is_honshimei || c?.is_main) st = 'nom'
  }
  // 4) マッピング
  return st === 'nom'   ? 'bg-danger text-white'
       : st === 'in'    ? 'bg-success text-white'
       : st === 'dohan' ? 'bg-secondary text-white'
       : st === 'help' ? 'bg-purple text-white'
       :                  'bg-blue text-white'
}
/* フリー⇄場内トグル + 本指/同伴からはフリーに戻す */
function toggleFreeInhouse(c) {
  const st = c.stay_type ?? (c.inhouse ? 'in' : 'free')

  // 本指・同伴 → タップでフリーに戻す
  if (st === 'nom' || st === 'dohan') {
    emit('setFree', c.id)
    return
  }

  const help = !!c.is_help

  if (st === 'in') {
    emit('setFree', c.id)
  } else if (st === 'free' && !help) {
    emit('setHelp', c.id)
  } else {
    emit('setInhouse', c.id)
  }
}

// 【本指×顧客機能】顧客選択モーダル
const showPickCustomer = ref(false)
const pendingMainCastId = ref(null)
const selectedCustomerIdForMain = ref(null)

function openMainWithCustomerPick(castId) {
  pendingMainCastId.value = castId
  if (props.billCustomers && props.billCustomers.length > 0) {
    const firstBc = props.billCustomers[0]
    selectedCustomerIdForMain.value = firstBc.customer_id ?? firstBc.customer
  } else {
    selectedCustomerIdForMain.value = null
  }
  showPickCustomer.value = true
}

function cancelPickCustomer() {
  showPickCustomer.value = false
  pendingMainCastId.value = null
  selectedCustomerIdForMain.value = null
}

function confirmPickCustomer() {
  if (!selectedCustomerIdForMain.value || !pendingMainCastId.value) {
    alert('顧客を選択してください')
    return
  }
  emit('setMainWithCustomer', {
    castId: pendingMainCastId.value,
    customerId: selectedCustomerIdForMain.value
  })
  showPickCustomer.value = false
  pendingMainCastId.value = null
  selectedCustomerIdForMain.value = null
}

function getCustomerDisplayName(bc) {
  const cid = bc.customer_id ?? bc.customer
  return bc.display_name || bc.customer_name || `Guest-${String(cid).padStart(6, '0')}`
}

if (import.meta.env.DEV) {
  // 今出ている配列が見たい時
  window.__cur = safeCurrent
  window.__bench = safeBench
}

</script>

<template>
  <div class="panel casts">
    <div class="wrap">
      <div class="d-flex p-2 justify-content-end">
        <div class="badge bg-blue df-center">フリー</div>→<div class="badge bg-success df-center">場内</div>→<div class="badge bg-purple df-center">ヘルプ</div>
      </div>
      <!-- 現在ついているキャスト -->
      <div class="now-cast mb-3">
        <div v-if="!safeCurrent.length" class="empty">未選択</div>
        <div v-else class="items">
          <div
            v-for="(c,i) in safeCurrent"
            :key="c?.id ?? i"
            class="item"
            :class="tagClass(c)"
          >
            <div class="wrap" @click="toggleFreeInhouse(c)">
              <div class="avatar">
                <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="40" class="rounded-circle" />
              </div>
              <div class="name">{{ c.stage_name }}</div>
            </div>
            <div class="d-flex align-items-center gap-1">
              <button v-if="c.stay_type !== 'nom'" class="btn btn-sm btn-danger" style="font-size:.7rem;padding:2px 6px;" @click.stop="openMainWithCustomerPick(c.id)">本指</button>
              <button v-if="c.stay_type !== 'dohan'" class="btn btn-sm btn-secondary text-white" style="font-size:.7rem;padding:2px 6px;" @click.stop="emit('setDohan', c.id)">同伴</button>
              <button class="text-white" @click.stop="emit('removeCast', c.id)" aria-label="remove">
                <IconX :size="16" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ベンチ（未選択） -->
      <div class="bench-cast">
        <!-- <div class="search">
          <input
            type="text"
            class="form-control"
            :value="keyword"
            @input="e => emit('update:keyword', e.target.value)"
          >
          <IconSearch :size="16" class="icon"/>
        </div> -->

        <div class="items">
          <div
            v-for="(c,i) in safeBench"
            :key="c?.id ?? i"
            class="item"
            :class="{ 'is-off': !isOnDuty(c) }"
          >
            <div class="wrap">
              <div class="avatar">
                <Avatar :url="c.avatar_url" :alt="c.stage_name" :size="40" />
              </div>
              <div class="name">{{ c.stage_name }}</div>
            </div>

            <!-- 出勤外はボタン非表示 -->
            <div class="button-area" v-if="isOnDuty(c)">
              <button class="btn btn-sm btn-secondary text-white" @click="emit('setDohan', c.id)">同伴</button>
              <button class="btn btn-sm btn-danger"  @click="emit('setMain', c.id)">本指</button>
              <button class="btn btn-sm bg-blue text-white" @click="emit('setFree', c.id)">フリー</button>
            </div>
          </div>
        </div>

      </div>
    </div>

    <div class="savebutton mt-5">
      <button class="btn btn-primary w-100" @click="$emit('save')">保存</button>
    </div>
  </div>

  <!-- 【本指×顧客機能】顧客選択モーダル -->
  <div
    v-if="showPickCustomer"
    class="pick-overlay"
    @click.self="cancelPickCustomer"
  >
    <div class="pick-dialog">
      <div class="pick-header">
        <div class="fw-bold">本指名の顧客を選択</div>
        <button type="button" class="btn-close" @click="cancelPickCustomer"></button>
      </div>
      <div class="pick-body">
        <div v-if="!billCustomers || billCustomers.length === 0" class="text-muted">
          顧客が登録されていません
        </div>
        <div v-else class="d-flex flex-column gap-2">
          <label
            v-for="bc in billCustomers"
            :key="bc.id"
            class="d-flex align-items-center gap-2 p-2 border rounded"
            :class="{ 'border-primary bg-primary bg-opacity-10': (bc.customer_id ?? bc.customer) === selectedCustomerIdForMain }"
            style="cursor: pointer;"
          >
            <input
              type="radio"
              :value="bc.customer_id ?? bc.customer"
              v-model="selectedCustomerIdForMain"
              class="form-check-input m-0"
            />
            <div class="flex-grow-1">
              <div class="fw-bold">{{ getCustomerDisplayName(bc) }}</div>
              <div v-if="bc.arrived_at" class="small text-muted">
                入店：{{ dayjs(bc.arrived_at).format('HH:mm') }}
              </div>
            </div>
          </label>
        </div>
      </div>
      <div class="pick-footer">
        <button type="button" class="btn btn-secondary" @click="cancelPickCustomer">キャンセル</button>
        <button type="button" class="btn btn-primary" @click="confirmPickCustomer">決定</button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.casts{
  .button-area{
    .btn{ white-space: nowrap; }
  }
}

.items .item.is-off{
  opacity: .45;
  filter: grayscale(100%);
  pointer-events: none;
  user-select: none;
}

.pick-overlay{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
}
.pick-dialog{
  width: min(520px, 100%);
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}
.pick-header, .pick-footer{
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pick-header{ border-bottom: 1px solid #eee; }
.pick-footer{ border-top: 1px solid #eee; gap: 8px; justify-content: flex-end; }
.pick-body{ padding: 12px; max-height: 60vh; overflow: auto; }
</style>
