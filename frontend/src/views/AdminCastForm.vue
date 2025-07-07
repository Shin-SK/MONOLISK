<!-- src/views/AdminCastForm.vue など --------------------------->
<script setup>
import { ref, onMounted, reactive, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
	api,
	getCastOptions, patchCastOption,
	searchCustomers, createCustomer,
	getShiftPlans,
} from '@/api'
import useZipcode from '@/utils/zipcode'

/* ---------- ルーティング ---------- */
const route	= useRoute()
const router = useRouter()
const isEdit = !!route.params.id					// id があれば「編集」

/* ---------- フォーム ---------- */
const form = ref({
	stage_name	: '',
	rank				: '',
	store			 : '',
	star_count	: 0,
	memo				: '',
	ng_customers: [],
	standby_places: [],
	price_mode	: 'DEFAULT',
})

const selectedTemplate = ref('')  


// ── 好きなだけ追加・編集できる ────────────────────
const addressTemplates = [
  { label: '満喫１', address: '東京都渋谷区○○1-1-1', zipcode: '1500041' },
  { label: '満喫２', address: '東京都渋谷区○○2-2-2', zipcode: '1500042' },
  { label: '満喫３', address: '東京都渋谷区○○3-3-3', zipcode: '1500043' },
]

function addFromTemplate(tpl) {
  // 既存行は全部リセット（手入力も前のテンプレも）
  form.value.standby_places = []
  form.value.standby_places.push(
    reactive({
      ...tpl,
      is_primary: false,   // 既定にはしない（必要ならここで true に）
      zipErr    : '',
	  is_manual: false,
    })
  )
  selectedTemplate.value = tpl.label
}



function makeBlankPlace () {
  const p = reactive({
    zipcode   : '',
    address   : '',
    label     : '',
    is_primary: false,
	is_manual:true, 
    zipErr    : '',
  })

  /* ---------------- useZipcode を呼び出す ---------------- */
  // ① ダミー（選択済みアドレス）
  const dummySelected = ref('__new__')

  // ② API が書き込むオブジェクト用の ref
  const newAddr = ref({ label: '', address: '' })

  // composable 実行
  const { zipcode, zipErr } = useZipcode(dummySelected, newAddr)

  /* ------- 双方向に同期させる ------- */
  // フォーム → composable
  watch(() => p.zipcode, v => { zipcode.value = v })

  // composable → フォーム
  watch(zipcode, v => { p.zipcode = v })
  watch(zipErr,  e => { p.zipErr  = e })
  watch(newAddr, val => {
    p.address = val.address               // 住所を自動挿入
    if (!p.label) p.label = val.label     // ラベルは自動入力があれば
  })

  return p
}

function detectTemplate () {
  const first = form.value.standby_places[0]
  if (!first || first.is_manual) {
    selectedTemplate.value = ''
    return
  }
  const hit = addressTemplates.find(t =>
    t.label   === first.label   &&
    t.address === first.address &&
    t.zipcode === first.zipcode
  )
  selectedTemplate.value = hit ? hit.label : ''
}



/* 歩合 (%) —— null なら未設定 */
const commission_pct = ref(null)

/* ---------- マスター ---------- */
const options	 = ref([])
const ranks		 = ref([])
const stores		= ref([])
const customers = ref([])

/* ---------- キャスト固有 ---------- */
const castOpts = ref([])	 // option の ON / OFF
const shifts	 = ref([])	 // シフト一覧

/* ---------- NG 顧客検索 ---------- */
const kwNg	 = ref('')
const candNg = ref([])
const showCand = ref(false)

const findNg = async () => {
	if (kwNg.value.length < 2) { showCand.value = false; return }
	candNg.value	= await searchCustomers(kwNg.value)
	showCand.value = candNg.value.length > 0
}
function addNg (c) {
	if (!form.value.ng_customers.includes(c.id))
		form.value.ng_customers.push(c.id)
	kwNg.value = ''; showCand.value = false
}
function removeNg (id) {
	form.value.ng_customers =
		form.value.ng_customers.filter(x => x !== id)
}
async function addNgNew () {
	const name	= prompt('顧客名');	 if (!name)	return
	const phone = prompt('電話番号'); if (!phone) return
	const newC	= await createCustomer({ name, phone })
	addNg(newC)
}



/* ---------- NG 顧客リスト ---------- */
// customers には API から取ってきた全顧客
const customerOptions = computed(() =>
  customers.value.map(c => ({
    id   : c.id,
    label: `${c.name} / ${c.phone}`
  }))
)

// v-model 用: 選択中オブジェクト配列
const ngSelected = computed({
  get: () =>
    form.value.ng_customers
         .map(id => customerOptions.value.find(o => o.id === id))
         .filter(Boolean),
  set: list => {
    form.value.ng_customers = list.map(o => o.id)
  }
})

// キーボード検索（名前 or 電話）
function customerFilter (option, search) {
  if (!search) return true
  return option.label.toLowerCase().includes(search.toLowerCase())
}



/* ---------- データ取得 ---------- */
async function fetchMasters () {
	const [opt, rks, sts, cust] = await Promise.all([
		api.get('options/').then(r => r.data),
		api.get('ranks/').then(r => r.data),
		api.get('stores/').then(r => r.data),
		api.get('customers/').then(r => r.data),
	])
	;[options.value, ranks.value, stores.value, customers.value] = [opt, rks, sts, cust]
}

async function loadRate () {
	if (!isEdit) return
	const latest = await api.get('cast-rates/', {
		params: {
			cast_profile: route.params.id,
			ordering		: '-effective_from',
			limit			 : 1,
		},
	}).then(r => r.data[0])
	commission_pct.value = latest?.commission_pct ?? null
}


/** ① 行追加・削除 */
function addPlace () { 
	form.value.standby_places.push(makeBlankPlace())
	selectedTemplate.value = ''	
	}
function removePlace(i){ form.value.standby_places.splice(i,1) }

async function fetchCast () {
	if (!isEdit) return

	Object.assign(
		form.value,
		await api.get(`cast-profiles/${route.params.id}/`).then(r => r.data),
	)

  // ★ 待機場所
  form.value.standby_places =
    form.value.standby_places.map(p =>
      // API には is_manual が無いので必ず false で付与
      reactive({ ...p, zipErr:'', zipcode:p.zipcode||'', is_manual:false })
    )

	castOpts.value = await getCastOptions(route.params.id)
	shifts.value	 = await getShiftPlans({ cast_profile: route.params.id })
	await loadRate()
	detectTemplate()
}

/* ---------- Option トグル ---------- */
async function toggleOpt (row) {
	row.is_enabled = !row.is_enabled
	await patchCastOption(row.id, { is_enabled: row.is_enabled })
}

/* ---------- 保存 ---------- */
async function save () {
	try {

		const payload = {
			...form.value,
		standby_places: form.value.standby_places.map(p => ({
			label		 : p.label,
			address	 : p.address,
			zipcode	 : p.zipcode,	 // ★忘れてた
			is_primary: p.is_primary,
		})),
		}
		/* 1) CastProfile 保存 */
		let castId
		if (isEdit) {
			await api.put(`cast-profiles/${route.params.id}/`, payload)
			castId = route.params.id
		} else {
			const { data } = await api.post('cast-profiles/', payload)
			castId = data.id
		}

		/* 2) 歩合 (%) を upsert	*/
		if (commission_pct.value !== null) {
			const today = dayjs().format('YYYY-MM-DD')

			// ── 既存を探す ─────────────────
			const latest = await api.get('cast-rates/', {
				params: { cast_profile: castId,
									effective_from: today,				// ちょうど今日付
									limit: 1 }
			}).then(r => r.data[0])

			if (latest) {
				// 既に「今日付」の行がある → PATCH
				await api.patch(`cast-rates/${latest.id}/`, {
					commission_pct: commission_pct.value
				})
			} else {
				// 無ければ INSERT
				await api.post('cast-rates/', {
					cast_profile	: castId,
					commission_pct: commission_pct.value,
					effective_from: today
				})
			}
		}

		router.push('/casts')
	} catch (e) {
		alert(e.response?.data?.detail || '保存失敗')
	}
}

watch(
  () => form.value.standby_places.map(p => ({
    label:p.label, address:p.address, zipcode:p.zipcode, is_manual:p.is_manual
  })),
  detectTemplate,
  { deep:true }
)

/* ---------- 初期化 ---------- */
onMounted(async () => {
	await fetchMasters()
	await fetchCast()

})
</script>


<template>
<div class="container-fluid py-4">
	
	<h1 class="h4 mb-3">{{ isEdit ? 'キャスト編集' : 'キャスト登録' }}</h1>

	<div class="d-grid gap-4" style="grid-template-columns: 1fr 1fr;">
		<div class="form-table-grid casts-area">

			<div class="outer">

				<div class="h5">源氏名</div>
				<input v-model="form.stage_name" class="form-control" placeholder="源氏名"/>

			</div>

			<div class="outer">

				<div class="h5">ランク</div>
				<select v-model="form.rank" class="form-select">
					<option v-for="r in ranks" :key="r.id" :value="r.id">{{ r.name }}</option>
				</select>

			</div>

			<div class="outer">
				<div class="h5">店舗</div>
				<select v-model="form.store" class="form-select">
					<option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
				</select>
			</div>

			<div class="outer">
				<div class="h5">歩合（％）</div>
				<input
					type="number"
					v-model.number="commission_pct"
					class="form-control"
					min="0"
					max="100"
				/>
			</div>

			<div class="outer">
				<div class="h5">待機場所</div>

				<div class="wrap">

					<!-- ① テンプレボタン行 ----------------------------->
					<div class="mb-2 d-flex flex-wrap gap-2">
					<button
						v-for="tpl in addressTemplates"
						:key="tpl.label"
						type="button"
						 :class="[
								'btn',
								selectedTemplate === tpl.label ? 'btn-primary' : 'btn-outline-primary'
								]"
						@click="addFromTemplate(tpl)"
					>
						{{ tpl.label }}
					</button>

					<!-- 手入力追加 -->
					<button type="button" class="btn btn-outline-secondary" @click="addPlace">
						＋ 追加
					</button>
					</div>


					<!-- 行 -->
					<div
						v-for="(p,i) in form.standby_places.filter(sp => sp.is_manual)"
						:key="i"
						>

						<div class="d-flex flex-column gap-4">
							<!-- 郵便番号 -->
							<div class="">
								<input v-model="p.zipcode" class="form-control" placeholder="郵便番号 1500041" />
								<small class="text-danger">{{ p.zipErr }}</small>
							</div>
							
							<!-- 住所 -->
							<div class="">
								<input v-model="p.address" class="form-control" placeholder="住所" />
							</div>

							<!-- ラベル -->
							<div class=" d-flex align-items-center gap-4 flex-shrink-0">
								<input v-model="p.label" class="form-control" placeholder="自宅/事務所などラベル入力"/>
								<!-- 既定 -->
								<div class="d-flex align-items-center">
									<input type="radio" class="btn-check"
												v-model="p.is_primary" :value="true"
												:id="`primary-${i}`"
												@change="form.standby_places.forEach((r,j)=>{ if(j!==i) r.is_primary=false })">
									<label
										:for="`primary-${i}`"
										class="btn btn-secondary text-nowrap">既定</label>
								</div>
							</div>


						</div>

						<!-- 削除ボタン -->
						<button v-if="form.standby_places.length>1"
										class="btn btn-sm btn-outline-danger mt-2"
										@click="removePlace(i)">
							削除
						</button>
					</div>
				</div><!-- wrap -->
			</div><!-- outer -->



			<div class="outer">

				<div class="h5">NG 顧客</div>
				
				<div class="wrap">
					<Multiselect
						v-model="ngSelected"
						:options="customerOptions"
						:searchable="true"
						:close-on-select="false"
						:multiple="true"
						:clear-on-select="false"
						placeholder="名前 / 電話 で検索"
						track-by="id"
						label="label"
						:filter="customerFilter"
					>
					</Multiselect>
				</div>

			</div>

			<div class="outer">

				<div class="h5">オプション（NGはチェックを外す）</div>

				<div class="wrap">

					<!-- 編集時: castOpts を表示 / 新規時: master options -->
					<div class="list-group" v-if="isEdit && castOpts.length">
						<label v-for="co in castOpts" :key="co.id"
							class="list-group-item d-flex align-items-center gap-2">
						<input type="checkbox" class="form-check-input mt-0"
								:checked="co.is_enabled"
								@change="toggleOpt(co)" />
						<span>{{ co.option_name }}</span>
						</label>
					</div>

					<!-- 新規登録フォームではマスタを全部 ON 状態で参考表示 -->
					<div class="list-group" v-else>
						<label v-for="o in options" :key="o.id"
							class="list-group-item d-flex align-items-center gap-2">
						<input type="checkbox" class="form-check-input mt-0" checked disabled />
						<span>{{ o.name }}</span>
						</label>
					</div>

				</div>

			</div>

			<div class="outer">

				<div class="h5">メモ</div>
				<textarea v-model="form.memo" rows="3" class="form-control"></textarea>
				
			</div>

		</div><!-- ftg -->

		<div class="shift">
			<div class="h5">登録シフト</div>

			<div class="wrap">

				<table class="table table-sm">
					<thead class="table-light"><tr><th>日付</th><th>開始</th><th>終了</th><th>状態</th></tr></thead>
					<tbody>
						<tr v-for="s in shifts" :key="s.id">
							<td>{{ s.date }}</td>
							<td>{{ s.start_at }}</td>
							<td>{{ s.end_at }}</td>
							<td>
								<span v-if="s.is_checked_in" class="badge bg-success">IN</span>
								<span v-else class="badge bg-secondary">予定</span>
							</td>
						</tr>
					</tbody>
				</table>

			</div>
		</div>
	</div>




<button
	type="button"
	class="btn btn-primary"
	@click="save"
>
	保存
</button>

</div>
</template>
