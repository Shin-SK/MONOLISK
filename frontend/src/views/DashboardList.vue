<!-- views/BillList.vue -->
<script setup>
/* ───── Imports ───── */
import { ref, onMounted, computed } from 'vue'
import dayjs              from 'dayjs'          // ← 忘れずに
import { useBills }       from '@/stores/useBills'
import BillModal          from '@/components/BillModal.vue'
import BillListCard       from '@/components/BillListCard.vue'
import { createBill, deleteBill } from '@/api'

/* ───── reactive state ───── */
const bills       = useBills()
const showModal   = ref(false)          // モーダル開閉フラグ
const currentBill = ref(null)          // モーダルに渡す 1 伝票
const selectedIds = ref(new Set())     // 一覧チェック用

// 追加：メモ展開中の bill.id を保持
const openMemoId = ref(null)
const toggleMemo = (id) => {
	openMemoId.value = (openMemoId.value === id ? null : id)
}
const hasMemo = (b) => !!(b?.memo && String(b.memo).trim())


/* ───── 初回ロード ───── */
onMounted(() => bills.loadAll(true))

/* ===== セグメント & アクティブのみ ===== */
const seg = ref('today')  // 'today' | 'yesterday' | 'last7' | 'last30' | 'thisMonth' | 'all' | 'range'
const dateFrom = ref(dayjs().format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))
const activeOnly = ref(false) // true=未精算(=closed_atなし)のみ

function rangeMs() {
	// デフォルト: seg='today'
	let from = dayjs().startOf('day'), to = dayjs().endOf('day')
	switch (seg.value) {
		case 'yesterday': from = dayjs().subtract(1,'day').startOf('day'); to = dayjs().subtract(1,'day').endOf('day'); break
		case 'last7':     from = dayjs().subtract(6,'day').startOf('day'); to = dayjs().endOf('day'); break
		case 'last30':    from = dayjs().subtract(29,'day').startOf('day');to = dayjs().endOf('day'); break
		case 'thisMonth': from = dayjs().startOf('month');                 to = dayjs().endOf('month'); break
		case 'range':     from = dayjs(dateFrom.value).startOf('day');     to = dayjs(dateTo.value).endOf('day'); break
		case 'all':       return { from: null, to: null }
	}
	return { from: from.valueOf(), to: to.valueOf() }
}

/* ★ フィルタ → 並べ替え（opened_at 新→旧） */
const sorted = computed(() => {
	const { from, to } = rangeMs()
	return [...bills.list]
		.filter(b => {
			if (activeOnly.value && b.closed_at) return false
			if (!from || !to) return true
			if (!b.opened_at) return false
			const t = dayjs(b.opened_at).valueOf()
			return t >= from && t <= to
		})
		.sort((a,b) => new Date(b.opened_at || 0) - new Date(a.opened_at || 0))
})

const MAP_SET = { setVIP:60, setMale:60, setFemale:60, set60:60 }

/* ───── 初回をドラフトにするやつ ───── */
function newBillDraft () {
  const draft = {
    id: null,                 // ← これで isNew 判定できる
    items: [],
    customers: [],
    stays: [],
    table: null,              // or { id:null, number:null }
    opened_at: null,          // BillModal 側の form で now が入る
    expected_out: null,
    grand_total: 0,
    paid_cash: 0,
    paid_card: 0,
    set_rounds: 0,
    ext_minutes: 0,
    // 必要なら table_id_hint なども
  }
  // いままでAPIで作っていた open() を、そのままドラフトで
  open(draft)
}


/* ───── 一覧クリック → 1件取得してモーダル ───── */
async function open(target) {
  // ドラフト（idなしオブジェクト）の場合はそのまま開く
  if (typeof target === 'object' && !target?.id) {
    currentBill.value = target
    showModal.value   = true
    return
  }
  // 既存IDの場合だけストアから取得
  await bills.open(target)
  currentBill.value = bills.current
  showModal.value   = true
}

/* ───── モーダル側から emit('saved') を受ける ───── */
function handleSaved() {
  showModal.value = false
  bills.loadAll(true)
}

/* ───── 新規伝票 ───── */
async function newBill () {
  const bill = await createBill({ table_id: 1, nominated_casts: [], inhouse_casts_w: [] })
  await bills.open(bill.id)           // 取った直後に open() で current へ
  currentBill.value = bills.current
  showModal.value   = true
}

/* ───── 一覧チェック & 削除 ───── */
function toggle(id){
  const set = selectedIds.value
  set.has(id) ? set.delete(id) : set.add(id)
}

async function bulkDelete () {
  if (!selectedIds.value.size) return
  if (!window.confirm(`${selectedIds.value.size} 件を削除しますか？`)) return
  // 1. まとめて並列で削除
  const ids = [...selectedIds.value]
  await Promise.all(ids.map(id => deleteBill(id)))

  // 2. UI 側の選択状態をクリア
  selectedIds.value.clear()

  // 3. キャッシュ無視で最新一覧を取得
  await bills.loadAll(true)
}

/* ---------- 伝票内ユーティリティ ---------- */

/* 任意：同じ日か判定するだけ */
function isSameDay(d1, d2){
  if (!d1 || !d2) return false
  return dayjs(d1).isSame(d2, 'day')
}

/* 人数計算：items から male/female を集計 */
function calcPax(b) {
  if (!b) return 0
  const items = b.items || []
  let male = 0, female = 0
  for (const it of items) {
    const code = it.master?.code || it.code || ''
    if (code.includes('Male')) male += (it.qty || 0)
    else if (code.includes('Female')) female += (it.qty || 0)
  }
  const total = male + female
  return total > 0 ? total : (b.pax || 0)
}

function liveCasts (b) {
  const map = new Map();        // castId → { stay , present , entered }

  (b.stays || []).forEach(s => {
    const id = s.cast?.id;
    if (!id) return;

    const present = !s.left_at;                         // ← ★いるかどうか
    const entered = new Date(s.entered_at).getTime();   //   比較用タイムスタンプ

    const prev = map.get(id);
    /* present の方を優先。present 同士／過去同士なら entered が新しい方 */
    if (
      !prev ||
      (present && !prev.present) ||
      entered > prev.entered
    ) {
      map.set(id, { stay: s, present, entered });
    }
  });

  return [...map.values()].map(({ stay, present }) => ({
    id     : stay.cast?.id,
    name   : stay.cast?.stage_name || "N/A",
    avatar : stay.cast?.avatar_url || "/img/user-default.png",
    color  : stay.stay_type === "nom" ? "danger"
           : stay.stay_type === "in"  ? "success"
           : stay.stay_type === "dohan"  ? "secondary"
           : "blue",
    present                                // ★ これでテンプレ側で判別
  }));
}


</script>

<template>
  <div class="dashboard list d-flex flex-column">
    <div class="outer flex-fill position-relative" style="min-width: 0;">
      <header class="d-flex flex-column">
        <div class="d-flex gap-1 mb-2">
          <div class="item badge text-white bg-danger">
            本指名
          </div>
          <div class="item badge text-white bg-success">
            場内
          </div>
          <div class="item badge text-white bg-blue">
            フリー
          </div>
        </div>
        <div class="d-flex flex-wrap gap-2 align-items-center my-3">
          <!-- アクティブのみ -->
          <div class="form-check form-switch m-0">
            <input class="form-check-input" type="checkbox" id="onlyActive" v-model="activeOnly">
            <label class="form-check-label small" for="onlyActive">アクティブのみ</label>
          </div>
        </div>
      </header>

    <div class="cards-container">
      <template
        v-for="(b, idx) in sorted"
        :key="b.id"
      >
        <!-- ★ 見出し行：前の伝票と日付が違えば出力 -->
        <div
          v-if="idx === 0 || !isSameDay(sorted[idx-1].opened_at, b.opened_at)"
          class="date-header"
        >
          {{ b.opened_at ? dayjs(b.opened_at).format('YYYY/MM/DD(ddd)') : '日付未定' }}
        </div>

        <!-- カード -->
        <BillListCard
          :bill="b"
          :isSelectable="false"
          @edit="open"
        />
      </template>
    </div>

      <div class="add-button position-fixed">
        <button
          class="btn btn-success rounded-circle"
          @click="newBillDraft"
        >
          <IconPlus />
        </button>
      </div>
    </div><!-- /outer -->

    <BillModal
      v-model="showModal"
      :bill="currentBill"
      @saved="handleSaved"
    />
  </div><!-- dashboard -->
</template>

<style scoped lang="scss">

.cards-container {
  display: grid;
  gap: 1rem;
  margin-bottom: 4rem;
}

.date-header {
  font-weight: bold;
  font-size: 1rem;
  padding: 1rem 0 0.5rem 0;
  color: #666;
  border-bottom: 1px solid #ccc;
}

  .bill-card {
.bill-card {
    position: relative;
    cursor: pointer;
    border: 1px solid #ddd;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

    &.closed::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(0, 0, 0, 0.3);
      pointer-events: none;
      border-radius: inherit;
    }
  }

  .card-header {
    background-color: white;
    .col{
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
    }
  }


  .card-footer {
    border-top: 1px solid #e9ecef;
    background-color: white;
  }

  .card-checkbox {
    position: absolute;
    top: 1rem;
    right: 1rem;
    input[type="checkbox"] {
      cursor: pointer;
    }
  }

  .label {
    font-size: 0.75rem;
    color: #666;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 0.25rem;
  }

  .value {
    font-size: 1.25rem;
    font-weight: bold;
    color: #333;
  }

  .memo-content {
    white-space: pre-wrap;
    word-break: break-word;
    padding: 0.5rem;
    background-color: #f9f9f9;
    border-radius: 4px;
    font-size: 0.875rem;
  }
}
</style>