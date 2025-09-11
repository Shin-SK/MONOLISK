<!-- src/components/panel/BasicsPanel.vue（PC/SP共通） -->
<script setup>
import { ref, reactive, computed, watch } from 'vue'

const props = defineProps({
	activePane: { type: String, default: 'base' },
	tables: { type: Array, default: () => [] },
	tableId:{ type: [Number, null], default: null },
	pax:    { type: Number, default: 1 },
	courseOptions: { type: Array, default: () => [] },

	/* SPだけ出す任意の顧客UI */
	showCustomer:       { type: Boolean, default: false },
	customerName:       { type: String,  default: '' },
	customerResults:    { type: Array,   default: () => [] },
	customerSearching:  { type: Boolean, default: false },
})

const emit = defineEmits([
	'update:tableId','update:pax','chooseCourse','jumpToBill',
	'clearCustomer','searchCustomer','pickCustomer','save'
])

/* ── SET回数 & 種類別人数 ── */
const rounds  = ref(0)       // 回数
const typeQty = reactive({}) // { [courseId]: 人数 }

const incRounds = () => (rounds.value = rounds.value + 1)
const decRounds = () => (rounds.value = Math.max(0, rounds.value - 1))

const qOf  = (id) => typeQty[id] ?? 0
const incT = (id) => (typeQty[id] = qOf(id) + 1)
const decT = (id) => (typeQty[id] = Math.max(0, qOf(id) - 1))

const totalHeadcount = computed(() =>
	(props.courseOptions || []).reduce((s,c) => s + (Number(typeQty[c.id])||0), 0)
)
const canConfirm = computed(() => rounds.value > 0 && totalHeadcount.value > 0)

/* ── フィードバック & 二重送信ガード ── */
const confirmBusy   = ref(false)   // 送信中ガード
const confirmedOnce = ref(false)   // 直近で「追加済み」表示
const confirmLabel  = computed(() => confirmedOnce.value ? '追加済み' : '確定')

/* 入力を変えたら「追加済み」表示を解除 */
watch(rounds, () => (confirmedOnce.value = false))
watch(typeQty,  () => (confirmedOnce.value = false), { deep:true })

/* 確定：種類ごとの人数 × SET回数 分だけ追加 → 会計へ（状態はリセットしない） */
const confirmSets = async () => {
	if (!canConfirm.value || confirmBusy.value) return
	confirmBusy.value = true
	try{
		const byId = new Map((props.courseOptions || []).map(c => [c.id, c]))
		for (const c of (props.courseOptions || [])) {
			const qtyPerType = Number(typeQty[c.id]) || 0
			if (qtyPerType <= 0) continue
			for (let r=0; r<rounds.value; r++) {
				emit('chooseCourse', byId.get(c.id), qtyPerType)
			}
		}
		confirmedOnce.value = true      // ★「追加済み」表示
		emit('jumpToBill')              // ★会計へ切替（親側でハンドル）
	} finally {
		// 連打防止：短いクールダウン
		setTimeout(() => (confirmBusy.value = false), 600)
	}
}

/* 顧客検索（SP用任意） */
const q = ref('')
const doSearch = () => emit('searchCustomer', q.value.trim())
</script>

<template>
  <div class="basics-panel gap-4 flex-column w-100"
       :class="{ 'd-none d-md-block': activePane !== 'base' }"
       style="display:flex;">

    <!-- テーブル -->
    <div class="wrap flex-fill" style="min-width:180px;">
      <div class="title mb-2"><IconPinned />テーブル</div>
      <select class="form-select w-100"
              :value="tableId"
              @change="e => emit('update:tableId', e.target.value ? Number(e.target.value) : null)">
        <option :value="null">-</option>
        <option v-for="t in (tables||[])" :key="t.id" :value="t.id">{{ t.number }}</option>
      </select>
    </div>

    <!-- 人数 -->
    <div class="wrap" style="min-width:140px;">
      <div class="title mb-2"><IconUsers />人数</div>
      <select class="form-select w-100"
              :value="pax"
              @change="e => emit('update:pax', Number(e.target.value))">
        <option v-for="n in 12" :key="n" :value="n">{{ n }}</option>
      </select>
    </div>

    <!-- SET回数 -->
    <div class="wrap" style="min-width:180px;">
      <div class="title mb-2"><IconHistoryToggle />SET数</div>
      <div class="d-flex justify-content-between align-items-center bg-light p-2 rounded">
        <div class="sub-title fw-bold ms-2">SET</div>
        <div class="d-inline-flex align-items-center gap-3 h-auto p-2 bg-white rounded-pill">
          <button type="button" class="btn p-0" @click="decRounds" :class="{ invisible: rounds<=0 }">
            <IconMinus :size="16" />
          </button>
          <span style="min-width:2ch; text-align:center;">{{ rounds }}</span>
          <button type="button" class="btn p-0" @click="incRounds">
            <IconPlus :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- 種類別人数（ステッパー） -->
    <div class="wrap flex-fill">
      <div class="sub-title mb-2"><IconListCheck />SET種類</div>
      <div class="d-flex flex-column gap-2">
        <div v-for="c in (courseOptions||[])" :key="c.id"
             class="d-flex justify-content-between align-items-center bg-light p-2 rounded">
          <div class="fw-bold ms-2">{{ c.label }}</div>
          <div class="d-inline-flex align-items-center gap-3 h-auto p-2 bg-white rounded-pill">
            <button type="button" class="btn p-0" @click="decT(c.id)" :class="{ invisible: qOf(c.id)<=0 }">
              <IconMinus :size="16" />
            </button>
            <span style="min-width:2ch; text-align:center;">{{ qOf(c.id) }}</span>
            <button type="button" class="btn p-0" @click="incT(c.id)">
              <IconPlus :size="16" />
            </button>
          </div>
        </div>
        <div class="form-text">合計: {{ totalHeadcount }} 名 × {{ rounds }} SET</div>
      </div>
    </div>

    <!-- 確定（状態表示付き） -->
    <div class="d-flex align-items-end">
      <button type="button"
              class="btn w-100"
              :class="confirmedOnce ? 'btn-success' : 'btn-warning'"
              :disabled="!canConfirm || confirmBusy"
              @click="confirmSets">
        {{ confirmLabel }}
      </button>
    </div>

    <!-- ▼ 顧客（SP時のみ） -->
    <div v-if="showCustomer" class="wrap flex-fill" style="min-width:220px;">
      <div class="title mb-2"><IconUserScan />顧客</div>

      <div class="d-flex align-items-center gap-2">
        <div class="form-control bg-light position-relative">
          {{ customerName || '未選択' }}
          <div class="button-area position-absolute"
               style="right:6px; top:50%; transform:translateY(-50%); display:flex; gap:6px;">
            <button class="btn btn-sm p-1" @click="doSearch"><IconSearch :size="16" /></button>
            <button class="btn btn-sm p-1" :disabled="!customerName" @click="$emit('clearCustomer')">
              <IconX :size="16"/>
            </button>
          </div>
        </div>
      </div>

      <div class="mt-2">
        <input class="form-control" type="text" v-model="q"
               placeholder="名前／TEL などで検索" @keyup.enter="doSearch">
      </div>

      <div v-if="customerSearching" class="small text-muted mt-2">検索中…</div>
      <ul v-if="customerResults && customerResults.length" class="mt-2 list-unstyled">
        <li v-for="(c,i) in customerResults" :key="c?.id ?? i"
            class="d-flex align-items-center gap-2 py-2 border-top">
          <div class="flex-grow-1">
            <div class="fw-bold">{{ c.alias || c.full_name || ('#'+c.id) }}</div>
            <div class="small text-muted">{{ c.phone || c.email || '' }}</div>
          </div>
          <button class="btn btn-sm btn-primary" @click="$emit('pickCustomer', c)">選択</button>
        </li>
      </ul>
      <div v-else-if="q" class="small text-muted mt-2">検索結果なし</div>

      <div class="d-grid gap-2 mt-2">
        <button class="btn btn-primary" @click="$emit('save')">保存</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.invisible{ visibility:hidden; width:0; padding:0 4px; }
.wrap{ margin-bottom:.5rem; }
.title{ font-weight:600; display:flex; align-items:center; gap:.4rem; }
.sub-title{ font-weight:600; display:flex; align-items:center; gap:.4rem; }
</style>
