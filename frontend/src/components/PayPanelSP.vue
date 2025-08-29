<script setup>
import { ref } from 'vue'
import dayjs from 'dayjs'

const props = defineProps({
  // 履歴リスト（確定済み）
  items: { type: Array, default: () => [] }, // [{id, name, qty, subtotal, served_by_cast, created_at/ordered_at/served_at?...}]

  // 名前解決
  masterNameMap: { type: Object, default: () => ({}) },
  servedByMap:   { type: Object, default: () => ({}) },

  // 集計表示
  current: { type: Object, default: () => ({ sub:0, svc:0, tax:0, total:0 }) },
  displayGrandTotal: { type: Number, default: 0 },

  // 入力状態
  settledTotal: { type: Number, default: 0 },
  paidCash:     { type: Number, default: 0 },
  paidCard:     { type: Number, default: 0 },
  billOpenedAt:  { type: String, default: '' },
  // 便利値
  diff:     { type: Number, default: 0 },   // paidTotal - targetTotal
  overPay:  { type: Number, default: 0 },
  canClose: { type: Boolean, default: false },
})

const emit = defineEmits([
  // 金額入力
  'update:settledTotal', 'update:paidCash', 'update:paidCard',
  'useGrandTotal', 'fillRemainderToCard', 'confirmClose',
  // 履歴編集
  'incItem', 'decItem', 'deleteItem'
])

// 数字入力ハンドラ（文字列→数値）
const onNum = (e, key) => {
  const v = Number(e.target.value ?? 0)
  emit(`update:${key}`, isNaN(v) ? 0 : v)
}

// 編集行のトグル
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

// 時刻の選び方（あるもの優先）
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
			<input class="form-control" type="number" :value="settledTotal" @input="e => onNum(e,'settledTotal')" />
			<!-- <button class="btn mini ms-2" type="button" @click="$emit('useGrandTotal')">＝伝票合計</button> -->
		</div>

		<div class="d-flex">
			<label class="d-flex align-items-center" style="width: 100px;">現金</label>
			<div class="position-relative w-100">
			<input class="form-control" type="number" :value="paidCash" @input="e => onNum(e,'paidCash')" />
			<button class="position-absolute end-0 top-0 bottom-0" type="button" @click="$emit('fillRemainderToCard')">
				<IconCalculator :size="16" />
			</button><!-- ★このボタンを押すと、金額関係なく会計金額が直でカードに入っちゃう -->
			</div>
		</div>

		<div class="d-flex">
			<label class="d-flex align-items-center" style="width: 100px;">カード</label>
			<input class="form-control" type="number" :value="paidCard" @input="e => onNum(e,'paidCard')" />
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
