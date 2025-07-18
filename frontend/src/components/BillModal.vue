<!-- src/components/BillModal.vue -->
<script setup>
/* -------------------------------------------------- *
 *  Imports                                           *
 * -------------------------------------------------- */
import { ref, computed, watch }   from 'vue'
import BaseModal                  from '@/components/BaseModal.vue'
import { useBills }               from '@/stores/useBills'
import { fetchMasters, fetchCasts, fetchTables, updateBill, deleteBillItem, getStore } from '@/api'

/* -------------------------------------------------- *
 *  Props / Emits / v‑model binding                   *
 * -------------------------------------------------- */
const props  = defineProps({ modelValue:Boolean, bill:Object })
const emit   = defineEmits(['update:modelValue'])

const visible = computed({
  get : () => props.modelValue,
  set : v => emit('update:modelValue', v),
})

/* bill が null の瞬間を安全に吸収 ------------------- */
const bill = computed(() => props.bill || {
  id: '',
  table : { id:null, number:'' },
  items : [],
  nominated_casts: [],
})

/* -------------------------------------------------- *
 *  Stores & local state                              *
 * -------------------------------------------------- */
const bills = useBills()

/* ------------------ テーブル一覧 ------------------- */
const tables  = ref([])              // 同一店舗の Table マスタ
const tableId = ref(null)            // v‑model 用（null = 未選択）
const tableLabel = computed(() => {
  const t = tables.value.find(t => t.id === tableId.value)
  return t ? t.number : ''
})

/* ------------------ キャスト関連 ------------------- */
const masters      = ref([])
const casts        = ref([])

const orderCasts = computed(() =>
  casts.value.filter(c => nominatedCasts.value.includes(c.id))
)

const searchHonshi = ref('')
const searchFree   = ref('')

const filteredHonshi = computed(() =>
  casts.value.filter(c =>
    c.stage_name.toLowerCase().includes(searchHonshi.value.toLowerCase()),
  ),
)
const filteredFree = computed(() =>
  casts.value.filter(c =>
    c.stage_name.toLowerCase().includes(searchFree.value.toLowerCase()) &&
    (nominationType.value === 'honshi' ? c.id !== mainCastId.value : true),
  ),
)

/* ------------------ 指名ステート ------------------- */
const mainCastId   = ref('')          // 本指名（単一）
const freeCastIds  = ref([])          // フリー（複数）
const inhouseSet   = ref(new Set())   // 場内

const nominationType = ref('')        // 'honshi' | 'free'
const activeTab      = ref('free')
watch(nominationType, v => { activeTab.value = v==='honshi'?'honshi':'free' })

const nominatedCasts = computed(() => {
  const ids = new Set([ mainCastId.value, ...freeCastIds.value ])
  return [...ids].filter(Boolean)
})
const hasChoice = computed(() => nominatedCasts.value.length > 0)

/* bill <‑> 指名同期 ------------------------------- */
watch(nominatedCasts, ids => { bill.value.nominated_casts = ids })

/* ------------------ Draft / Pending --------------- */
const draft = ref({ master_id:'', qty:1, cast_id:'' })
const pendingItems = ref([])          // 未確定注文プレビュー

function addDraftToPending () {
  if (!draft.value.master_id || draft.value.qty <= 0) return

  // master_id を数値化
  const mid = typeof draft.value.master_id === 'object'
                ? draft.value.master_id.id
                : Number(draft.value.master_id)

  const cid = typeof draft.value.cast_id === 'object'
                ? draft.value.cast_id.id
                : draft.value.cast_id || null

  pendingItems.value.push({
    master_id : mid,
    qty       : draft.value.qty,
    cast_id   : cid
  })
  Object.assign(draft.value, { master_id:'', qty:1, cast_id:'' })
}

/* ------------------ 料金レート ------------------- */
const serviceRate = ref(0.10)   // 初期値 (万一失敗しても 10%)
const taxRate     = ref(0.10)

// 金額フォーマッタ
const yen = n => `¥${n.toLocaleString()}`

// ★ 明細集計 (確定 + pending)
const confirmedSubtotal = computed(() =>
  bill.value.items.reduce((s, it) => s + it.subtotal, 0)
)
const pendingSubtotal = computed(() =>
  pendingItems.value.reduce((s, it) => {
    const m = masters.value.find(m => m.id === it.master_id)
    return s + (m ? m.price_regular * it.qty : 0)
  }, 0)
)
const subTotal       = computed(() => confirmedSubtotal.value + pendingSubtotal.value)
const serviceCharge  = computed(() => Math.round(subTotal.value * serviceRate.value))
const tax            = computed(() => Math.round((subTotal.value + serviceCharge.value) * taxRate.value))
const grandTotal     = computed(() => subTotal.value + serviceCharge.value + tax.value)

/* ------------ セット時間 ------------- */
const setMasters = computed(() =>
	masters.value.filter(m => m.category==='set').sort((a,b)=>a.duration_min-b.duration_min)
)
const extMaster  = computed(() => masters.value.find(m => m.category==='ext' && m.duration_min===30))

/* ----- Toggle ----- */
const showCustom	= ref(false)			// ← 追加：入力欄の表示フラグ
const customDur		= ref('')				// 数値を入れるだけ

function toggleCustom(){
	showCustom.value = !showCustom.value	// ON/OFF
	if(!showCustom.value) customDur.value = ''
}

/* ---------------- テーブル編集トグル ---------------- */
const editingTable = ref(false)        // ← pencil 押下で true
const draftTableId = ref(null)         // select 用一時バッファ

function startEditTable () {
  draftTableId.value = tableId.value   // 現在値をコピー
  editingTable.value = true
}

function cancelEditTable () {          // × or Esc 用
  editingTable.value = false
}

function applyTable () {               // ✔️ 保存
  tableId.value       = draftTableId.value
  editingTable.value  = false
}

/* ------------ コースマスタ ------------- */
const courseMap = computed(() => {
	const map = {}
	masters.value.forEach(m => { map[m.code] = m })   // code は自由に合わせて
	return map
})

/* ------------ コース選択 ------------- */

/* ==== コース表示名マッピング ========================= */
const labelMap = {
  set60      : 'SET60',
  set60_vip  : 'VIP60',
  ext30      : '延長30',
  ext30_vip  : 'VIP延長30',
}

/* ==== 並び順を固定したオプション ===================== */
const courseOrder = ['set60', 'set60_vip', 'ext30', 'ext30_vip']
const courseOptions = computed(() =>
  courseOrder
    .map(code => {
      const m = masters.value.find(v => v.code === code)
      return m ? { ...m, label: labelMap[code] || m.name } : null
    })
    .filter(Boolean)
)


/* ▼ プルダウンに並べるコース一覧 */
const courseMasters = computed(() =>
  masters.value
    .filter(m => ['set', 'ext'].includes(m.category))
    .sort((a, b) =>        // 並べ替えはご自由に
      (a.category === b.category)
        ? a.duration_min - b.duration_min      // 例: 60→90→30…
        : a.category.localeCompare(b.category) // set → ext
    )
)

/* ▼ v‑model 用ステート */
const selectedCode = ref('')   // <select> で選ばれた code
const pax          = ref(1)    // 人数入力（qty に相当）

/* ▼ 追加処理（人数 × コース＝1行） */
async function addSelectedCourse () {
  const m = courseMasters.value.find(v => v.code === selectedCode.value)
  if (!m)  { alert('コースを選択してください'); return }
  if (pax.value <= 0) { alert('人数を入力してください'); return }

  await bills.addItem({
    item_master : m.id,
    name        : m.name,
    price       : m.price_regular,
    qty         : pax.value,
  })
  // 入力リセット
  selectedCode.value = ''
  pax.value = 1
  await bills.reload()
}


 /* ----- 追加（EXT） ----- */
 async function addExtension () {              // ← ここはそのまま
	if (!extMaster.value) return alert('延長マスタがありません')
	await bills.addItem({
		item_master : extMaster.value.id,
		name        : extMaster.value.name,
		price       : extMaster.value.price_regular,
		qty         : 1,
	})
	await bills.reload()
 }
/* -------------------------------------------------- *
 *  Bill 読込時の初期化                               *
 * -------------------------------------------------- */
watch(
  () => bill.value.id,
  async id => {
    if (!id) return
    const storeId = bill.value.table.store
    // ★ 追加: 店舗レート取得
    try {
      const store = await getStore(storeId)
      const sr = Number(store.service_rate)
      const tr = Number(store.tax_rate)

	  serviceRate.value = sr >= 1 ? sr / 100 : sr
	  taxRate.value     = tr >= 1 ? tr / 100 : tr
    } catch (_) {
      console.warn('store rate fetch failed; fallback 10%')
    }

    ;[masters.value, casts.value, tables.value] = await Promise.all([
      fetchMasters(storeId),
      fetchCasts(storeId),
      fetchTables(storeId),
    ])

    tableId.value        = bill.value.table.id ?? null
    mainCastId.value     = bill.value.nominated_casts?.[0] || ''
    freeCastIds.value    = bill.value.nominated_casts?.slice(1) || []
    inhouseSet.value     = new Set(bill.value.inhouse_casts || [])
  },
  { immediate:true },
)

/* ------------------ 場内トグル -------------------- */
async function toggleInhouse (cid) {
  const set = inhouseSet.value
  set.has(cid) ? set.delete(cid) : set.add(cid)
  await bills.setInhouseStatus([...set])
}

/* ------------------ 削除モード ------------------ */
const deleteMode   = ref(false)
const selectedIds  = ref(new Set())

function toggleDeleteMode () {
  deleteMode.value = !deleteMode.value
  selectedIds.value.clear()
}

function toggleSelect (id) {
  const set = selectedIds.value
  set.has(id) ? set.delete(id) : set.add(id)
}

async function confirmDelete () {
  if (!selectedIds.value.size) return
  if (!confirm('選択した注文を削除しますか？')) return

  for (const id of selectedIds.value) {
    await deleteBillItem(bill.value.id, id)
  }
  selectedIds.value.clear()
  deleteMode.value = false
  await bills.reload()
}

/* ------------------ 閉じるボタン ------------------ */

function close () {
  // v‑model を介して親へ false を返すだけで OK
  visible.value = false         // → emit('update:modelValue', false)
}

/* -------------------------------------------------- *
 *  保存                                              *
 * -------------------------------------------------- */
async function save () {
  /* ① pendingItems → 確定品目へ */
  for (const it of pendingItems.value) {
    const m = masters.value.find(m => m.id == it.master_id)
    await bills.addItem({
      item_master    : m.id,
      name           : m.name,
      price          : m.price_regular,
      qty            : it.qty,
      back_rate      : m.default_back_rate,
      served_by_cast : it.cast_id || null,
    })
  }
  pendingItems.value = []

  /* ② ヘッダ / 指名 PATCH */
  const payload = {
    nominated_casts : nominatedCasts.value,
    inhouse_casts_w : [...inhouseSet.value],
  }
  if (tableId.value) payload.table_id = tableId.value
  await updateBill(bill.value.id, payload)

  alert('保存しました')
  await bills.reload()
}
</script>

<template>
  <BaseModal v-model="visible">
	<div class="modal-header d-flex justify-content-between align-items-center">
		<div class="table-number-area text-center">
			<div class="head d-flex gap-4 ">
				<span class="d-flex align-items-center me-2 bg-light px-4">
					<i class="bi bi-sticky-fill me-2"></i>{{ bill.id }}
				</span>

				<div class="d-flex align-items-center bg-light px-4">

					<!-- ───── 表示モード ───── -->
					<template v-if="!editingTable">
						<span class="me-2 d-flex gap-2">
							<i class="bi bi-fork-knife"></i>{{ tableLabel || '未選択' }}
						</span>

						<!-- 編集アイコン -->
						<button class="btn btn-sm btn-outline-secondary"
								@click="startEditTable" title="テーブルを変更">
						<i class="bi bi-pencil"></i>
						</button>
					</template>

					<!-- ───── 編集モード ───── -->
					<template v-else>
						<select class="form-select me-2"
								v-model="draftTableId" style="width:8rem;">
							<option v-for="t in tables" :key="t.id" :value="t.id">
								{{ t.number }}
							</option>
						</select>

						<!-- 決定 / キャンセル -->
						<button class="btn btn-sm btn-primary me-1" @click="applyTable">
							<i class="bi bi-check-lg"></i>
						</button>
						<button class="btn btn-sm btn-outline-secondary" @click="cancelEditTable">
							<i class="bi bi-x-lg"></i>
						</button>
					</template>

				</div>
							
				<!-- コース -->
				<div class="d-flex gap-2 me-2" role="group">
				<template v-for="m in courseOptions" :key="m.code">
					<input  class="btn-check"
							type="checkbox"
							:id="`c-${m.code}`"
							:value="m.code"
							v-model="selectedCode">
					<label class="d-flex align-items-center btn btn-outline-primary"
						:for="`c-${m.code}`">
					{{ m.label }}
					</label>
				</template>
				</div>

				<!-- 人数 -->
				<input type="number" min="1" v-model.number="pax"
						class="form-control text-end" style="width:60px;" placeholder="人数">

				<!-- 追加ボタン -->
				<button class="btn btn-dark" @click="addSelectedCourse">
					<i class="bi bi-cart-plus-fill"></i>
				</button>
			</div>
		</div>
		<button class="btn-close mb-auto" @click="close"></button>
	</div>

	<div class="modal-body">
		<div class="wrapper d-grid h-100" style="grid-template-columns: 1fr 1fr;">
			<div class="outer p-3 d-flex flex-column">





				<!-- 選択結果エリア -->
				<div class="choiced-area mb-5">
					<!-- 選択結果エリア -->
					<div class="d-flex flex-wrap gap-2 justify-content-center p-3 bg-light">
					<template v-if="hasChoice">
						<template v-for="cid in nominatedCasts" :key="cid">
						<!-- 本指名：表示だけ -->
						<div v-if="cid === mainCastId"
							class="bg-white rounded px-4 py-3 position-relative border border-warning">
							{{ casts.find(c => c.id === cid)?.stage_name || 'N/A' }}
							<span class="badge bg-warning text-dark ms-1">本指名</span>
						</div>

						<!-- フリー：カード全体がトグル -->
							<template v-else>
							<div  class="bg-white rounded px-4 py-3 position-relative border border-primary text-primary"
									:class="inhouseSet.has(cid)"
									style="cursor:pointer;"
									@click="toggleInhouse(cid)">
								{{ casts.find(c => c.id === cid)?.stage_name }}

								<span class="badge ms-2"
									:class="inhouseSet.has(cid)
											? 'bg-primary text-light'
											: 'bg-light text-primary'">
								場内
								</span>
							</div>
							</template>
						</template>
					</template>

					<span v-else class="text-muted">キャストを選択してください</span>
					</div>

				</div>

				<!-- ───────── キャスト選択 ───────── -->
				<div class="cast-area mb-5">
					<!-- タブ見出し -->
					<div class="d-flex tab-menu mb-2">
						<div class="flex-fill d-flex justify-content-center">
							<button class="tab-item px-2"
									:class="{active: activeTab==='honshi'}"
									@click="activeTab='honshi'">本指名</button>
							</div>
						<div class="flex-fill d-flex justify-content-center">
							<button class="tab-item px-2"
									:class="{active: activeTab==='free'}"
									@click="activeTab='free'">フリー</button>
						</div>
					</div>

					<!-- タブ中身 -->
					<div class="tab-area">
						<!-- 本指名（単一） -->
						<div v-if="activeTab==='honshi'">
						<!-- 検索 -->
						<input type="text" v-model="searchHonshi" placeholder="本指名キャスト検索"
								class="form-control w-100 mb-4 text-center">
						<div class="d-flex flex-wrap gap-4 justify-content-center" role="group">
							<template v-for="c in filteredHonshi" :key="c.id">
							<input class="btn-check" type="radio"
									:id="'main-'+c.id" :value="c.id" v-model="mainCastId">
							<label class="btn"
									:class="mainCastId===c.id ? 'btn-primary' : 'btn-outline-primary'"
									:for="'main-'+c.id">{{ c.stage_name }}</label>
							</template>
						</div>
						</div>

						<!-- フリー（複数） -->
						<div v-if="activeTab==='free'">
						<input type="text" v-model="searchFree" placeholder="フリーキャスト検索"
								class="form-control w-100 mb-4 text-center">
						<div class="d-flex flex-wrap gap-4 justify-content-center" role="group">
							<template v-for="c in filteredFree" :key="c.id">
							<input class="btn-check" type="checkbox"
									:id="'free-'+c.id" :value="c.id" v-model="freeCastIds">
							<label class="btn"
									:class="freeCastIds.includes(c.id)
											? 'btn-primary':'btn-outline-primary'"
									:for="'free-'+c.id">{{ c.stage_name }}</label>
							</template>
						</div>
						</div>
					</div>
				</div><!-- /cast-area -->


			</div><!-- /outer -->
			<div class="outer p-3 d-flex flex-column">

				<!-- ───────── 注文フォーム ───────── -->
				<div class="order-form mb-4 d-flex flex-column" style="min-height: 50%;">
					<!-- <h5 class="text-center mb-3">注文</h5> -->

					<div class="d-grid align-items-stretch gap-2 mb-4" style="grid-template-columns: 40% 40% 10% auto;">

						<Multiselect
						v-model="draft.cast_id"
						:options="casts"
						:disabled="!orderCasts.length"
						value-prop="id"
						track-by="id"
						label="stage_name"
						placeholder="- CAST -"
						:searchable="true"
						:close-on-select="true"
						:show-labels="false"
						:select-label="''"
						:selected-label="''"
						:deselect-label="''"
						class="w-auto"
						/>

							<!-- メニュー選択 -->
						<Multiselect
						v-model="draft.master_id"
						:options="masters"
						value-prop="id"
						track-by="id"
						label="name"
						placeholder="- ITEM -"
						:searchable="true"
						:close-on-select="true"
						:show-labels="false"
						:select-label="''"
						:selected-label="''"
						:deselect-label="''"
						class="w-auto"
						/>

						<!-- 数量 -->
						<input type="number" min="1"
							v-model.number="draft.qty"
							class="form-control text-end flex-grow-1"
							style="min-width: 30px;"
							>
						<!-- 仮追加 -->
						<button class="btn btn-dark text-light"
								@click="addDraftToPending">
							<i class="bi bi-cart-plus-fill"></i>
						</button>

					</div>
					<!-- 未確定注文プレビュー（テーブル表示） -->
					<table class="table table-bordered table-hover align-middle table-striped">
						<thead>
							<tr>
							<th>品名</th>
							<th style="width:70px;">個数</th>
							<th>注文キャスト</th>
							<th style="width:56px;">操作</th>
							</tr>
						</thead>
						<tbody v-if="pendingItems.length">
							<tr v-for="(it, i) in pendingItems" :key="i">
							<!-- 品名 -->
							<td>
								{{ masters.find(m => m.id === it.master_id)?.name || '??' }}
							</td>

							<!-- 数量 -->
							<td class="text-end">{{ it.qty }}</td>

							<!-- キャスト -->
							<td>
								<span v-if="it.cast_id">
								{{ casts.find(c => c.id === it.cast_id)?.stage_name || '-' }}
								</span>
								<span v-else>-</span>
							</td>

							<!-- 削除 -->
							<td class="text-center">
								<button class="btn text-danger"
										title="この行を削除"
										@click="pendingItems.splice(i, 1)">
								<i class="bi bi-dash-circle"></i>
								</button>
							</td>
							</tr>
						</tbody>
					</table>
					<button class="btn btn-primary me-2 w-100 mt-auto" @click="save">保存</button>
				</div>


				<div class="order-list mt-5 mt-auto">

					<!-- ───────── 明細テーブル ───────── -->
					<h4 class="text-center">注文一覧</h4>
					
					<table class="table table-bordered table-hover align-middle table-striped">
					<thead>
						<tr>
							<th v-if="deleteMode" style="width:32px;"></th>
							<th>品名</th>
							<th>個数</th>
							<th>注文キャスト</th>
							<th>単価</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="it in bill.items" :key="it.id">
							<td v-if="deleteMode" class="text-center">
								<input type="checkbox"
									:value="it.id"
									:checked="selectedIds.has(it.id)"
									@change="toggleSelect(it.id)" />
							</td>
							<td>{{ it.name }}</td>
							<td>{{ it.qty }}</td>
							<td>{{ it.served_by_cast_name || '-' }}</td>
							<td>{{ it.subtotal.toLocaleString() }}</td>
						</tr>
					</tbody>
					</table>


					<div class="d-flex gap-4">
						<!-- 削除確定ボタン（モード中のみ表示）-->
						<div v-if="deleteMode" class="text-end mb-3">
						<button class="btn btn-danger"
								:disabled="!selectedIds.size"
								@click="confirmDelete">
							選択した注文を削除
						</button>
						</div>
						<button  class="btn btn-sm"
								:class="deleteMode ? 'btn-outline-secondary' : 'btn-outline-secondary'"
								@click="toggleDeleteMode">
								<!-- :disabled="bill.closed_at"これ追加すると「締め後は削除できない」にできる -->
							{{ deleteMode ? 'キャンセル' : '削除' }}
						</button>
					</div>	

					<!-- 料金サマリ -->
					<div class="total-sum mt-auto">
						<table class="table table-sm mb-0">
							<tbody>
							<tr>
								<th class="w-50">小計</th>
								<td class="text-end">{{ yen(subTotal) }}</td>
							</tr>
							<tr>
								<th>サービス料 ({{ (serviceRate*100).toFixed(0) }}%)</th>
								<td class="text-end">{{ yen(serviceCharge) }}</td>
							</tr>
							<tr>
								<th>消費税 ({{ (taxRate*100).toFixed(0) }}%)</th>
								<td class="text-end">{{ yen(tax) }}</td>
							</tr>
							<tr class="table-primary fw-bold">
								<th>合計</th>
								<td class="text-end">{{ yen(grandTotal) }}</td>
							</tr>
							</tbody>
						</table>
					</div>
					
					<button class="btn btn-success mt-5 w-100"
							@click="bills.closeCurrent()"
							:disabled="bill.closed_at">
						締める
					</button>

				</div>


			</div><!-- /outer -->
		</div>
	</div>

	<!-- フッター -->
	<template #footer>

	</template>
  </BaseModal>
</template>

