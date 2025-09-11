<script setup>
import { ref, watch, computed } from 'vue'
import dayjs from 'dayjs'

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
})
const emit = defineEmits([
  'update:settledTotal','update:paidCash','update:paidCard',
  'useGrandTotal','fillRemainderToCard','confirmClose',
  'incItem','decItem','deleteItem'
])

/* ▼ ここから追加：自動同期（手動編集したらロック） */
const dirtyTotal = ref(false) // true の間は自動同期しない

const calcTotal = computed(() => Number(props.current?.total) || 0)

watch(
  () => props.current.total,
  () => { if (!dirtyTotal.value) emit('update:settledTotal', calcTotal.value) },
  { immediate: true }
)

const effectiveTotal = computed(() => {
  const grand = Number(props.displayGrandTotal) || 0
  const cur   = Number(props.current?.total)   || 0
  return grand > 0 ? grand : cur
})


const needsUpdate = computed(() =>
  dirtyTotal.value || Number(props.settledTotal || 0) !== calcTotal.value
)

const resetToTotal = () => {
  dirtyTotal.value = false
  emit('update:settledTotal', calcTotal.value)   // ← 上の「合計」と揃える
}

/* ▲ ここまで追加 */

const setExactCash = () => {
  const total = Math.max(0, Number(props.settledTotal) || 0)
  emit('update:paidCash', total)
  emit('update:paidCard', 0)
}
const setExactCard = () => {
  const total = Math.max(0, Number(props.settledTotal) || 0)
  emit('update:paidCash', 0)
  emit('update:paidCard', total)
}

const onNum = (e, key) => {
  const v = Number(e.target.value ?? 0)
  if (key === 'settledTotal') dirtyTotal.value = true   // 手動編集でロック
  emit(`update:${key}`, isNaN(v) ? 0 : v)
}

const editingId = ref(null)
const toggleEdit = (id) => { editingId.value = (editingId.value === id ? null : id) }

const onDec = (it) => {
  const q = Number(it?.qty) || 0
  if (q <= 1) {
    const name = it?.name || props.masterNameMap[String(it.item_master)] || `#${it.item_master}`
    if (confirm(`${name} を削除しますか？`)) {
      emit('deleteItem', it)
      if (editingId.value === it.id) editingId.value = null
    }
  } else {
    emit('decItem', it)
  }
}

const pickTime = (it) =>
  it?.ordered_at || it?.served_at || it?.created_at || it?.updated_at || props.billOpenedAt || null
const fmtTime  = (t) => t ? dayjs(t).format('YYYY/M/D HH:mm') : ''
</script>


<template>
  <div class="panel pay">
	<div class="d-flex flex-column gap-4">
		<!-- ▼ 履歴（確定済みの注文） -->
		<div class="history-list d-flex flex-column gap-3">
		<div
			v-for="it in items"
			:key="it.id"
			class="card d-flex flex-row justify-content-between"
		>
			<!-- 左：アイテム情報 -->
			<div class="item-area p-2 d-flex flex-column gap-2 flex-grow-1">
			<div class="d-flex align-items-center gap-2 text-secondary" style="font-size:1rem;">
				<div class="id">#{{ it.id }}</div>
				<div class="time d-flex align-items-center gap-1">
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

			<!-- 右：編集ボタン or 数量ステッパー -->
			<div class="d-flex align-items-center">
			<!-- 数量ステッパー -->
			<div class="cartbutton d-flex align-items-center">
			<div class="d-flex align-items-center gap-3 bg-white h-auto p-2 m-2" style="border-radius:100px;">
				<button type="button" @click="onDec(it)"><IconMinus :size="16" /></button>
				<span>{{ it.qty }}</span>
				<button type="button" @click="$emit('incItem', it)"><IconPlus :size="16" /></button>
			</div>
			</div>
			</div>
		</div>

		<div v-if="!items || !items.length" class="text-muted small">履歴はありません</div>
		</div>

     <!-- ▼ サマリ -->
      <div class="sum">
        <div class="d-grid gap-3" style="grid-template-columns: 1fr auto;">
          <div class="label">小計</div>      <div class="value text-end">¥{{ current.sub.toLocaleString() }}</div>
          <div class="label">サービス料</div><div class="value text-end">¥{{ current.svc.toLocaleString() }}</div>
          <div class="label">消費税</div>    <div class="value text-end">¥{{ current.tax.toLocaleString() }}</div>
          <div class="label fw-bold fs-5">合計</div><div class="value fw-bold text-end fs-5">¥{{ current.total.toLocaleString() }}</div>
        </div>
      </div>

      <!-- ▼ 支払い -->
      <div class="payment d-flex flex-column gap-3">
        <div class="d-flex">
          <label class="d-flex align-items-center" style="width: 100px;">会計金額</label>
          <div class="position-relative w-100">
            <input class="form-control" type="number" :value="settledTotal" @input="e => onNum(e,'settledTotal')" />
            <!-- 手動編集 or 乖離時のみ出す。押すと自動同期に戻る -->
            <button
              class="position-absolute top-0 bottom-0 end-0 px-2"
              type="button"
              @click="resetToTotal"
              title="合計に合わせる"
            ><IconRefresh :size="16"/></button>
          </div>
        </div>

        <div class="d-flex">
          <label class="d-flex align-items-center" style="width: 100px;">現金</label>
          <div class="position-relative w-100">
            <input class="form-control" type="number" :value="paidCash" @input="e => onNum(e,'paidCash')" />
            <button class="position-absolute end-0 top-0 bottom-0" type="button" @click="setExactCash" title="全額を現金で支払い">
              <IconTransferVertical :size="16" />
            </button>
          </div>
        </div>

        <div class="d-flex">
          <label class="d-flex align-items-center" style="width: 100px;">カード</label>
		  	<div class="position-relative w-100">
				<input class="form-control" type="number" :value="paidCard" @input="e => onNum(e,'paidCard')" />
				<button class="position-absolute end-0 top-0 bottom-0" type="button" @click="$emit('fillRemainderToCard')">
					<IconCalculator :size="16" />
				</button>
			</div>
        </div>

        <div class="small text-muted">
          伝票合計: ¥{{ displayGrandTotal.toLocaleString() }} /
          受領合計: ¥{{ (Number(paidCash||0)+Number(paidCard||0)).toLocaleString() }} /
          差額: <span :class="diff===0 ? 'ok' : 'neg'">¥{{ diff.toLocaleString() }}</span>
          <span v-if="overPay>0" class="text-danger ms-1">（お釣り: ¥{{ overPay.toLocaleString() }}）</span>
        </div>
      </div>

      <!-- ▼ 確定 -->
      <div class="paybutton">
        <button class="btn btn-primary w-100" type="button" :disabled="!canClose" @click="$emit('confirmClose')">お会計</button>
      </div>
	</div>
  </div>
</template>
