<!-- views/BillList.vue -->
<script setup>
/* ───── Imports ───── */
import { ref, onMounted, computed } from 'vue'
import dayjs              from 'dayjs'          // ← 忘れずに
import { useBills }       from '@/stores/useBills'
import BillModal          from '@/components/BillModal.vue'
import Avatar        from '@/components/Avatar.vue'
import { createBill, deleteBill } from '@/api'

/* ───── reactive state ───── */
const bills       = useBills()
const showModal   = ref(false)          // モーダル開閉フラグ
const currentBill = ref(null)          // モーダルに渡す 1 伝票
const selectedIds = ref(new Set())     // 一覧チェック用

/* ───── 初回ロード ───── */
onMounted(() => bills.loadAll())

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
          <!-- リストだけリアルタイムってかリストって感じで -->
          <div class="item badge text-white bg-danger">
            本指名
          </div>
          <div class="item badge text-white bg-success">
            場内
          </div>
          <div class="item badge text-white bg-blue">
            フリー
          </div>
          <!-- <div class="item badge text-white bg-warning">
            フリー(~20分)
          </div>
          <div class="item badge text-white bg-orange">
            フリー(~30分)
          </div> -->
        </div>
          <!-- ▼ セグメント & アクティブ -->
        <div class="d-flex flex-wrap gap-2 align-items-center my-3">
          <!-- セグメント -->
          <div class="btn-group btn-group-sm" role="group">
            <button class="btn btn-outline-secondary" :class="{active:seg==='today'}"     @click="seg='today'">今日</button>
            <button class="btn btn-outline-secondary" :class="{active:seg==='yesterday'}" @click="seg='yesterday'">昨日</button>
            <button class="btn btn-outline-secondary" :class="{active:seg==='last7'}"     @click="seg='last7'">7日</button>
            <button class="btn btn-outline-secondary" :class="{active:seg==='last30'}"    @click="seg='last30'">30日</button>
            <button class="btn btn-outline-secondary" :class="{active:seg==='thisMonth'}" @click="seg='thisMonth'">今月</button>
            <button class="btn btn-outline-secondary" :class="{active:seg==='all'}"       @click="seg='all'">全期間</button>
            <button class="btn btn-outline-secondary" :class="{active:seg==='range'}"     @click="seg='range'">期間</button>
          </div>
          <!-- 期間指定 -->
          <div v-if="seg==='range'" class="d-flex align-items-center gap-1">
            <input type="date" class="form-control form-control-sm" v-model="dateFrom" />
            <span>〜</span>
            <input type="date" class="form-control form-control-sm" v-model="dateTo" />
          </div>
          <!-- アクティブのみ -->
          <div class="form-check form-switch m-0">
            <input class="form-check-input" type="checkbox" id="onlyActive" v-model="activeOnly">
            <label class="form-check-label small" for="onlyActive">アクティブのみ</label>
          </div>
        </div>
      </header>
    <div class="table-responsive-md">
      <table
        class="bill-table table table-hover align-middle"
        style="table-layout: fixed;"
      >
        <colgroup>
          <col style="width:  40px">  <!-- チェック -->
          <col style="width:  40px">  <!-- ID -->
          <col style="width:  40px">  <!-- 卓 -->
          <col style="width:  40px">  <!-- SET -->
          <col style="width:  80px">  <!-- in -->
          <col style="width:  40px">  <!-- 延長 -->
          <col style="width:  80px">  <!-- out -->
          <col style="width: 300px">   <!-- ★ キャスト：残り全部 -->
          <col style="width: 160px">  <!-- 小計 -->
          <col style="width: 160px">  <!-- 合計 -->
        </colgroup>
        <thead>
          <tr>
            <th />
            <th class="text-center">
              ID
            </th>
            <th class="text-center">
              卓
            </th>
            <th class="text-center">
              SET
            </th>
            <th class="text-center">
              in
            </th>
            <th class="text-center">
              延長
            </th>
            <th class="text-center">
              out
            </th>
            <th class="text-center">
              キャスト
            </th>
            <th class="text-end">
              小計
            </th>
            <th class="text-end">
              合計
            </th>
          </tr>
        </thead>
        <tbody>
          <template
            v-for="(b, idx) in sorted"
            :key="b.id"
          >
            <!-- ★ 見出し行：前の伝票と日付が違えば出力 -->
            <tr
              v-if="idx === 0 || !isSameDay(sorted[idx-1].opened_at, b.opened_at)"
              class="bg-light"
            >
              <td
                :colspan="10"
                class="text-start fw-bold"
              >
                {{ b.opened_at ? dayjs(b.opened_at).format('YYYY/MM/DD(ddd)') : '日付未定' }}
              </td>
            </tr>
            <tr
              class="main"
              :class="b.closed_at ? 'table-close text-muted' : ''"
              @click="open(b.id)"
            >
              <td class="text-center">
                <input
                  type="checkbox"
                  :value="b.id"
                  :checked="selectedIds.has(b.id)"
                  @click.stop="toggle(b.id)"
                >
              </td>
              <td class="text-center">
                {{ b.id }}
              </td>
              <td class="text-center">
                {{ b.table?.number ?? '‑' }}
              </td>
              <td class="text-center">
                {{ b.set_rounds || '‑' }}
              </td>
              <td class="text-center">
                <span class="fs-3 fw-bold">
                  {{ b.opened_at ? dayjs(b.opened_at).format('HH:mm') : '‑' }}
                </span>
              </td>
              <td class="text-center">
                <span>{{ b.ext_minutes ? Math.floor(b.ext_minutes/30) : '‑' }}</span>
              </td>
              <td class="text-center">
                <span class="fs-3 fw-bold">{{ b.expected_out ? dayjs(b.expected_out).format('HH:mm') : '‑' }}</span>
              </td>
          
              <td>
                <!-- ── 今ついているキャスト ─────────────────── -->
                <div class="d-flex flex-wrap gap-2 mb-1 align-items-start" style="min-width:0">
                  <div
                    v-for="p in liveCasts(b).filter(p => p.present)"
                    :key="p.id"
                    class="d-flex align-items-center btn text-light p-2"
                    :class="`bg-${p.color}`"
                  >
                    <Avatar
                      :url="p.avatar"
                      :alt="p.name"
                      :size="16"
                      class="me-1"
                    />
                    <span class="fw-bold">{{ p.name }}</span>
                  </div>
                </div>

                <!-- ── 過去に付いたキャスト ────────────────── -->
                <div class="d-flex flex-wrap gap-1 past">
                  <span
                    v-for="p in liveCasts(b).filter(p => !p.present)"
                    :key="p.id"
                    class="badge bg-secondary-subtle text-dark small"
                  >
                    {{ p.name }}
                  </span>
                </div>
              </td>
              <td class="text-end">
                {{ b.subtotal.toLocaleString() }}
              </td>
              <td class="text-end">
                {{ (b.settled_total ?? (b.closed_at ? b.total : b.grand_total)).toLocaleString() }}
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
      <!-- ★ 削除ボタン -->
      <button
        class="btn btn-danger mt-4"
        :disabled="!selectedIds.size"
        @click="bulkDelete"
      >
        <IconTrash /> 削除
      </button>

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

tr.main td{
  padding:16px 4px;
  .past{
    margin-top: 1rem;
  }
}

.table-close, .table-close td{
  padding:8px !important;
  .fs-3{
    font-size: 14px !important;
  }
  .fw-bold{
    font-weight: normal !important;
  }
  .past{
    margin: auto !important;
  }
}


</style>