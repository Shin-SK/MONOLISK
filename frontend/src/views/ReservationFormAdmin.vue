<script setup>
/* ===============================================================
 * ReservationFormAdmin.vue – 管理者予約フォーム
 * =============================================================== */
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { asyncComputed }        from '@vueuse/core'
import { useRoute, useRouter }  from 'vue-router'
import debounce                 from 'lodash.debounce'
import dayjs                    from 'dayjs'
import ReservationCastSelector  from '@/components/ReservationCastSelector.vue'
import {
  getStores, getCustomers, getDrivers, getCourses,
  getOptions, getCastProfiles, getPrice,
  searchCustomers, createCustomer,
  createReservation, updateReservation, getReservation,
  getLatestReservation, getCustomerAddresses, createCustomerAddress, getReservationChoices
} from '@/api'

/* ──────────────── props / emit ──────────────── */
const props = defineProps({
  reservationId : { type:[Number,String], default:null },
  inModal       : { type:Boolean, default:false }
})
const emit = defineEmits(['saved'])

/* ──────────────── helpers ──────────────── */
const toId = v => (v && typeof v === 'object') ? v.id : v
const driverById = id => opts.drivers.find(d => d.id === Number(id)) || null

/* ===== OPTION 選択 ===== */
const selectedOptions   = ref([])        // <Multiselect v-model 用
const selectedOptionIds = computed(() =>
  (Array.isArray(selectedOptions.value) ? selectedOptions.value : [])
    .map(o => typeof o === 'object' ? o.id : o)
    .map(Number)
    .filter(Number.isFinite)
	.filter(Boolean) 
)

/* ──────────────── 基本 state ──────────────── */
const route  = useRoute()
const router = useRouter()
const currentId = computed(() => props.reservationId ?? route.params.id ?? null)
const isEdit    = computed(() => !!currentId.value)

/* ──────────────── フォーム値 ──────────────── */
const form = reactive({
  reservation_type:'normal',
  stores:[], cast_profiles:[],
  start_at:'', course:'',
  driver_PU:null, driver_DO:null,
  customer:'', deposited_amount:0, received_amount:0,
  pay_card:0,  pay_cash:0,
  revenues:[{label:'',amount:0}],
  expenses:[{label:'',amount:0}],
  extend_blocks:0,
  change_amount:'',
  status: null,
  pay_cash : 0,              // ← 現金受取額（＝旧 received_amount）
  pay_card : 0,              // ← カード決済額
  deposited_amount : 0,      // 店に入金した現金
  change_amount   : '',      // 釣り銭
})

/* ──────────────── マスタ ──────────────── */
const opts = reactive({ stores:[], customers:[], drivers:[], courses:[], options:[] })
const styles = ['綺麗系','可愛い系','モデル']
const cupSizes= ['A','B','C','D','E']
const choices = ref({ status: [] })

/* ──────────────── キャスト検索 ──────────────── */
const castsByStore = ref({})
const visibleCasts = computed(() =>
  Object.values(castsByStore.value).flat()
)
const fetchCasts = debounce(async () => {
  const params = {}
  const storeIds = filter.storeIds.map(toId)
  if (storeIds.length) params.store = storeIds.join(',')
  if (filter.style)   params.style     = filter.style
  if (filter.cup)     params.cup_size  = filter.cup
  if (filter.keyword.trim()) params.q  = filter.keyword.trim()

  castsByStore.value = { all: await getCastProfiles(params) }

  /* 所属外キャストを除外 */
  form.cast_profiles = form.cast_profiles.filter(id =>
    visibleCasts.value.some(c => c.id === id)
  )
}, 400)

/* ──────────────── filter box ──────────────── */
const filter = reactive({ storeIds: [], style:'', cup:'', keyword:'' })
watch([() => [...filter.storeIds].sort(), () => filter.style,
       () => filter.cup, () => filter.keyword.trim()],
      fetchCasts, { deep:true })

/* ──────────────── マスタ取得 ──────────────── */
async function fetchMasters () {
  const [s,c,d,co,o] = await Promise.all([
    getStores(), getCustomers(), getDrivers(), getCourses(), getOptions()
  ])
  Object.assign(opts,{stores:s,customers:c,drivers:d,courses:co,options:o})
}

/* ──────────────── 編集モード読み込み ──────────────── */
async function fetchReservation () {
  if (!isEdit.value) return
  const res = await getReservation(currentId.value)

  Object.assign(form,{
    stores      : res.store ? [res.store] : [],
    start_at    : res.start_at.slice(0,16),
    course      : res.casts[0]?.course ?? '',
    customer    : res.customer,
    driver_PU   : driverById(res.drivers?.find(d=>d.role==='PU')?.driver),
    driver_DO   : driverById(res.drivers?.find(d=>d.role==='DO')?.driver),
    deposited_amount: res.deposited_amount ?? 0,
    received_amount : res.received_amount  ?? 0,
	change_amount    : res.change_amount ?? 0,
    reservation_type: res.reservation_type,
    pay_card: res.payments.find(p=>p.method==='card')?.amount || 0,
    pay_cash: res.payments.find(p=>p.method==='cash')?.amount || 0,
	status       : res.status,
  })

	/* マニュアル売上・経費をフォームへ展開 ------------------------- */
	const rev = res.manual_entries?.filter(e => e.entry_type === 'revenue') ?? []
	const exp = res.manual_entries?.filter(e => e.entry_type === 'expense') ?? []

	form.revenues = rev.length ? rev.map(e => ({ label: e.label, amount: +e.amount })) 
								: [{ label: '', amount: 0 }]

	form.expenses = exp.length ? exp.map(e => ({ label: e.label, amount: +e.amount }))
								: [{ label: '', amount: 0 }]


  /* ★ 開始日時を入力用 ref に反映 */
  const dt = dayjs(res.start_at)             // ISO → dayjs
  startDate.value = dt.format('YYYY-MM-DD')  // DatePicker
  startTime.value = dt.format('HH:mm')       // time input

  selectedOptions.value = res.charges
    .filter(ch=>ch.kind==='OPTION')
    .map(ch => opts.options.find(o => o.id === Number(
           typeof ch.option === 'object' ? ch.option.id : ch.option
         )))
    .filter(Boolean)

  /* --- ★ 送迎場所を引き継ぐ ----------------------- */
  // 顧客住所帳を取得
  addresses.value = await getCustomerAddresses(res.customer)

  if (res.address_book) {
    // 住所帳レコードで保存されていた
    selectedAddress.value = res.address_book           // id が入る
  } else if (res.address_text) {
    // テキスト直書きで保存されていた
    selectedAddress.value = '__new__'
    newAddress.value      = { label: '', address_text: res.address_text }
  } else {
    // 何も選ばれていなかった
    selectedAddress.value = ''
  }

  await fetchCasts()
  form.cast_profiles = res.casts.map(c =>
    typeof c.cast_profile === 'object' ? c.cast_profile.id : c.cast_profile
  )
}

/* ──────────────── 日付・時刻 ──────────────── */
const startDate = ref(dayjs().format('YYYY-MM-DD'))
const startTime = ref('')
watch([startDate,startTime],() => {
  form.start_at = `${startDate.value}T${startTime.value||'00:00'}`
},{immediate:true})

/* ─────────── 顧客（電話検索） ─────────── */
const phone       = ref('')
const candidates  = ref([])
const showList    = ref(false)

/* 3 文字以上で検索 */
const fetchCandidates = debounce(async () => {
  if (phone.value.length < 3) { showList.value = false; return }
  candidates.value = await searchCustomers(phone.value)
  showList.value   = candidates.value.length > 0
}, 400)

/* 選択中の顧客オブジェクト */
const selectedCustomer = computed(
  () => opts.customers.find(c => c.id === form.customer) || null
)

/* 候補クリック時 */
function choose (c){
  if (!opts.customers.some(x => x.id === c.id)) opts.customers.push(c)
  form.customer = c.id
  phone.value   = c.phone
  showList.value= false
}

/* 新規登録 */
async function registerNew (){
  const name = prompt('顧客名'); if (!name) return
  const address = prompt('住所') || ''
  const newCust = await createCustomer({ name, phone: phone.value, address })
  choose(newCust)
}

/* 顧客解除 */
function clearCustomer (){
  form.customer = ''
  phone.value   = ''
  showList.value= false
}

/* 最新予約 & 住所帳 */
const latest           = ref(null)
const addresses        = ref([])
const selectedAddress  = ref('')
const newAddress       = ref({ label:'', address_text:'' })

/* 顧客が決まるたびに取得 */
watch(() => form.customer, async id => {
  if (!id){
    latest.value      = null
    addresses.value   = []
    selectedAddress.value = ''
    return
  }
  latest.value     = await getLatestReservation(id)
  addresses.value  = await getCustomerAddresses(id)
})


/* ──────────────── 金額計算 ──────────────── */
const castPriceSum = asyncComputed(async () => {
  if (!form.course || !form.cast_profiles.length) return 0
  return await getPrice({
    course: form.course,
    cast_profile: form.cast_profiles.map(toId)
  })
},0)

const optionPriceSum = computed(() =>
  selectedOptionIds.value
    .map(id => opts.options.find(o=>o.id===id)?.default_price ?? 0)
    .reduce((a,b)=>a+b,0)
)

const revenueSum  = computed(() =>
  form.revenues.reduce((t, r) => t + (+r.amount || 0), 0)
)

const expenseSum = computed(() =>
  form.expenses.reduce((t, e) => t + (+e.amount || 0), 0)
)

const extendUnit = computed(() =>
  visibleCasts.value.find(c=>c.id===form.cast_profiles[0])?.extend_price_30 || 0
)
const extendPriceSum = computed(() => form.extend_blocks * extendUnit.value)


 /** ───────── 見積金額 (粗利-経費) ───────── */
 const price = computed(() => {
   const gross =
     (+castPriceSum.value   || 0) +
     (+optionPriceSum.value || 0) +
     (+extendPriceSum.value || 0) +
     form.revenues.reduce((t, r) => t + (+r.amount || 0), 0)
 
   const expense =
     form.expenses.reduce((t, e) => t + (+e.amount || 0), 0)
 
   return gross - expense
 })


 const paymentTotal = computed(() =>
  (+form.pay_cash || 0) + (+form.pay_card || 0)
)
const paymentDiff = computed(() =>
  paymentTotal.value - price.value
)


/* ── お釣りのヒント ── */
const suggestedChange = computed(() =>
  Math.max(0, (+form.received_amount || 0) - (+form.pay_cash || 0))
)


/* ─── data ─── */
const isRecvManual = ref(true)

// 0) カード or 小計 が変わったら必ず現金を再計算
watch([() => form.pay_card, price], () => {
  // 現金 = 小計 – カード（マイナスにはさせない）
  form.pay_cash = Math.max(0, price.value - (+form.pay_card || 0))

  // 釣り銭を更新
  form.change_amount = Math.max(
    0,
    (+form.received_amount || 0) - (+form.pay_cash || 0)
  )
})

// ① pay_cash が変わったら、手入力していない限り受取金にコピー
watch(() => form.pay_cash, () => {
  // 釣り銭も更新
  form.change_amount = Math.max(
    0,
    (+form.received_amount || 0) - (+form.pay_cash || 0)
  )
})

// ② 受取金が変わっても「入力済みなら」触らない
watch(() => form.received_amount, () => {
  if (form.change_amount === '' || form.change_amount == null) {
    form.change_amount = suggestedChange.value      // ← 初期入力を補完したいなら
  }
})

/* ──────────────── 保存 ──────────────── */
async function save () {
const optionIds = selectedOptionIds.value
const castIds   = form.cast_profiles.map(toId)
const minutes   = opts.courses.find(c => c.id === form.course)?.minutes ?? 0

const payload = {
  /* 基本 */
  reservation_type : form.reservation_type,
  store            : form.stores[0],
  customer         : form.customer || null,
  start_at         : new Date(form.start_at).toISOString(),
  total_time       : minutes + form.extend_blocks * 30,
  deposited_amount : form.deposited_amount,
  received_amount : form.received_amount,
  extend_blocks    : form.extend_blocks,
  change_amount    : form.change_amount || 0,
...(form.status ? { status: form.status } : {}),

  /* キャスト × コース */
  casts   : castIds.map(id => ({ cast_profile: id, course: form.course })),

  /* ドライバー */
  drivers : [
    ...(form.driver_PU ? [{ role: 'PU', driver: toId(form.driver_PU) }] : []),
    ...(form.driver_DO ? [{ role: 'DO', driver: toId(form.driver_DO) }] : [])
  ],

  /* 支払い */
  payments : [
    ...(form.pay_cash ? [{ method: 'cash', amount: +form.pay_cash }] : []),
    ...(form.pay_card ? [{ method: 'card', amount: +form.pay_card }] : []),
  ],

  /* マニュアル売上／経費 */
  manual_entries : [
	...form.revenues
	.filter(e => +e.amount)                    // ❶ 金額が 0 でないものだけ送る
	.map(e => ({
		entry_type: 'revenue',
		label : e.label?.trim() || '',           // ❷ ラベルが空でも OK
		amount: +e.amount
	})),
	...form.expenses
	.filter(e => +e.amount)
	.map(e => ({
		entry_type: 'expense',
		label : e.label?.trim() || '',
		amount: +e.amount
	}))
  ],

  /* オプション */
  charges : optionIds.map(id => ({ kind: 'OPTION', option: id }))
  
}

	/* 住所帳を組み込む */
	if (selectedAddress.value === '__new__') {
	if (!newAddress.value.address_text.trim()) {
		alert('住所を入力してください'); return
	}
	const created = await createCustomerAddress(form.customer, newAddress.value)
	payload.address_book = created.id
	} else {
	payload.address_book = selectedAddress.value || null
	}

	try {
	const id = isEdit.value
		? (await updateReservation(currentId.value, payload), currentId.value)
		: (await createReservation(payload)).id

	emit('saved', { id })

	if (!props.inModal) await router.push('/reservations')
	} catch (e) {
		console.error(e.response?.data)          // ← ここだけで十分
	}
}

/* ──────────────── 初期化 ──────────────── */
onMounted(async () => {
  await fetchMasters()
  await fetchReservation()
  await fetchCasts()
  choices.value = await getReservationChoices()
  if (import.meta.env.DEV) {
    // ブラウザ Console から window.rows で参照できる
    window.rows = rows;
  }
})

/* ──────────────── dev logs ──────────────── */
if (import.meta.env.DEV){
  watch(selectedOptions,v=>console.log('▶ options',JSON.stringify(v)),{deep:true})
}
watch(
  () => [form.revenues, form.expenses],
  () => {
    console.log('revenues', JSON.stringify(form.revenues))
    console.log('expenses', JSON.stringify(form.expenses))
  },
  { deep: true }
)
</script>


<template>
<div class="form form-admin container-fluid">
	<h1 class="h3 mb-4">
		{{ isEdit ? `予約編集` : '新規予約' }}
	</h1>

	<div class="form-admin">
	<div class="form-admin__wrap">
		<div class="customer-area outer">

			<div class="search">
				<div v-if="!selectedCustomer" class="input-area">
					<!-- 入力 -->
					<input v-model="phone" @input="fetchCandidates"
						class="form-control" placeholder="090…" />

					<div class="add">
						<button @click="registerNew"><span class="material-symbols-outlined">add_circle</span></button>
					</div>
				</div>

				<div class="list-area"><!-- 候補 -->
					<ul v-if="showList" class="d-flex gap-4 mt-4 flex-wrap">
						<li v-for="c in candidates" :key="c.id"
							class="btn btn-outline-primary"
							@click="choose(c)">
							<span class="fw-bold d-block">{{ c.name }}</span>
							<span class="fs-6">{{ c.phone }}</span>
						</li>
					</ul>
				</div>


				<!-- 選択済み表示 -->
				<div v-if="selectedCustomer" class="selected p-2 bg-white rounded d-flex align-items-center justify-content-between">
					<div class="btn btn-outline-primary d-flex gap-2">
						<span class="fw-bold">{{ selectedCustomer.name }}</span>
						<span class="fs-6">{{ selectedCustomer.phone }}</span>
					</div>
					<button class="btn btn-outline-secondary" @click="clearCustomer">
						変更
					</button>
				</div><!-- selected -->

			</div><!-- search -->


			<div v-if="latest" class="latest-carte card mt-3">
				<div class="card-header">前回の予約</div>
				<div class="card-body">
					<div class="card-area">
						<div class="wrap image">
							<div v-for="rc in latest.casts" :key="rc.cast_profile" class="">
								<RouterLink :to="`/reservations/${latest.id}`">
								<img :src="rc.avatar_url || '/static/img/cast-default.png'">
								</RouterLink>
							</div>
						</div>
						<div class="wrap text">
							<div class="items">
								<span class="badge bg-secondary">{{ latest.store_name }}</span>
							</div>
							<div class="items">
								<span class="fw-bold">
									{{ new Date(latest.start_at).toLocaleString() }}
								</span>
							</div>
							<div v-for="rc in latest.casts" :key="rc.cast_profile" class="items">
								<span class="fw-bold">{{ rc.stage_name }}</span>
							</div>
							<div v-for="c in latest.courses" :key="c.cast" class="items">
								<span>
									{{ c.minutes }}分コース
								</span>
							</div>
							<ul class="items">
								<!-- オプションが1件以上あるとき -->
								<template v-if="latest.options && latest.options.length">
									<li
									v-for="o in latest.options"
									:key="o.option_id"
									class="badge bg-secondary"
									>
									{{ o.name }}
									</li>
								</template>

								<!-- 0件のとき -->
								<li v-else class="text-muted">
									オプションはありません
								</li>
							</ul>
							<div class="items">
								<span>{{ latest.expected_amount.toLocaleString() }} 円</span>
							</div>
							<div class="items memo"	v-if="latest.customer_memo">
								<div class="wrap">
									<span>
										{{ latest.customer_memo }}
									</span>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div><!-- /latest-carte -->

		</div><!-- customer-area	-->
		<div class="cast-area outer">

			<div class="cast-search">
				<div class="cast-search__wrap">
					<div class="wrap">
						<Multiselect
							v-model="filter.storeIds" 
							:options="opts.stores"
							:object="false"
							:multiple="true"
							value-prop="id"
							:searchable="false"
							:close-on-select="false"
							:show-labels="false"
							label="name"
							track-by="id"
							placeholder="店舗"
						/>
					</div><!-- wrap -->

					<!-- スタイル（1つだけ選択）-->
					<div class="wrap">
						<Multiselect
							v-model="filter.style"
							:options="styles"
							:object="false"
							:multiple="true"
							value-prop="id"
							:searchable="false"
							:close-on-select="false"
							:show-labels="false"
							placeholder="系統"
							clear
						/>
					</div><!-- wrap -->

					<!-- カップサイズ -->	
					<div class="wrap">
						<Multiselect
							v-model="filter.cup"
							:options="cupSizes"
							:object="false"
							:multiple="true"
							value-prop="id"
							:searchable="false"
							:close-on-select="false"
							:show-labels="false"
							placeholder="カップ"
							clear
						/>
					</div><!-- wrap -->

					<div class="wrap">
							<input
							v-model="filter.keyword"
							class="form-control"
							placeholder="キーワード検索"
							@keyup.enter="fetchCasts"
						/>
					</div>

				</div><!-- __wrap -->
			</div>

			<!-- ◆ キャスト選択 ◆ -->
			<div class="casts">
				<div class="bg-white py-4">
					<ReservationCastSelector
					:casts="visibleCasts"
					v-model:modelValue="form.cast_profiles"
					/>
				</div>
			</div>
		</div>
		<div class="form-area outer">
			<div class="form-area__wrap">
				<div class="area status">
					<div class="h5">ステータス</div>
					<div class="wrap d-flex flex-wrap gap-3">
						<template v-for="opt in choices.status" :key="opt[0]">
						<!-- opt = ["BOOKED", "Booked"] -->
						<input class="btn-check"
								type="radio"
								:id="`st-${opt[0]}`"
								v-model="form.status"
								:value="opt[0]"/>
						<label class="btn btn-outline-primary"
								:class="{active: form.status === opt[0]}"
								:for="`st-${opt[0]}`">
							{{ opt[1] }}
						</label>
						</template>
					</div>
				</div>
				<!-- 送迎場所 -->
				<div class="area">
					<div class="h5">送迎場所</div>
					<div class="wrap">
					<div class="d-flex flex-wrap gap-3" role="group">
						<!-- 既存 -->
						<label
							v-for="a in addresses"
							:key="a.id"
							class="btn btn-outline-primary"
							:class="{ active: selectedAddress === a.id }"
						>
							<input
								type="radio"
								class="btn-check"
								v-model="selectedAddress"
								:value="a.id"
							/>
							{{ a.label }} / {{ a.address_text }}
						</label>

						<!-- 新規 -->
						<label
							class="btn btn-outline-success"
							:class="{ active: selectedAddress === '__new__' }"
						>
							<input
								type="radio"
								class="btn-check"
								v-model="selectedAddress"
								value="__new__"
							/>
							＋ 新規住所
						</label>
					</div>
					<!-- 新規入力フォーム -->
					<div v-if="selectedAddress === '__new__'" class="mt-3">
						<input
							v-model="newAddress.label"
							class="form-control mb-2"
							placeholder="例）ホテルA"
						/>
						<textarea
							v-model="newAddress.address_text"
							class="form-control"
							placeholder="住所を入力"
							rows="3"
						></textarea>
					</div>
					</div>
				</div> <!-- area -->

				<!-- 開始日時 -->
				<div class="area start-date">
					<div class="h5">開始日時</div>
					<!-- 日付ピッカー：手入力も可 -->
					<div class="wrap">
						<DatePicker
							v-model:value="startDate"
							type="date"
							value-type="format"
							format="YYYY-MM-DD"
							:editable="true"
							input-class="form-control"
							clearable
						/>

						<!-- 時刻は手入力メイン -->
						<input type="time"
								v-model="startTime"
								class="form-control"
								placeholder="HH:mm" />
					</div>

				</div>

				<!-- コース -->
				<div class="area">
					<div class="h5">コース</div>
					<div class="d-flex flex-wrap gap-3" role="group" aria-label="Courses">
						<template v-for="c in opts.courses" :key="c.id">
						<!-- hidden radio -->
						<input	class="btn-check" type="radio"
								:id="`course-${c.id}`"
								v-model="form.course"
								:value="c.id" autocomplete="off">
						<!-- label -->
						<label class="btn btn-outline-primary"
								:class="{ active: form.course === c.id }"
								:for="`course-${c.id}`">
							{{ c.minutes }}min<span v-if="c.is_pack">（パック）</span>
						</label>
						</template>
					</div>
				</div>

				<!-- ◆ オプション ◆ -->
				<div class="area">
				<div class="h5">オプション</div>

						<!-- vue-multiselect 版（ID 配列をそのまま保持）-->
					<Multiselect
						v-model="selectedOptions"
						:options="opts.options"
						label="name"
						track-by="id"
						:multiple="true"
						placeholder="オプションを選択"
					/>

				</div>

				<!-- ドライバー -->
				<div class="area driver">
					<div class="h5">ドライバー</div>
					<div class="wrap">
						<Multiselect
						v-model="form.driver_PU"
						:options="opts.drivers"
						label="name"
						track-by="id"
						placeholder="迎え"
						:searchable="false"
						clearable
						/>

						<!-- ドライバー (Drop-Off) -->
						<Multiselect
						v-model="form.driver_DO"
						:options="opts.drivers"
						label="name"
						track-by="id"
						placeholder="送り"
						:searchable="false"
						clearable
						/>
					</div>
				</div>

				<!-- ◆ 予約種類 ◆ -->
				<div class="area">
					<div class="h5">予約種類</div>
					<div class="btn-group" role="group">
						<input class="btn-check" type="radio" id="type-normal"
							v-model="form.reservation_type" value="normal">
						<label class="btn btn-outline-primary"
							:class="{active: form.reservation_type==='normal'}"
							for="type-normal">通常予約</label>

						<input class="btn-check" type="radio" id="type-hime"
							v-model="form.reservation_type" value="hime">
						<label class="btn btn-outline-danger"
							:class="{active: form.reservation_type==='hime'}"
							for="type-hime">姫予約</label>
					</div>
				</div>

				<!-- ◆ マニュアル売上 ◆ -->
				<div class="area">
					<div class="h5">マニュアル売上</div>
					<div class="wrap">
						<div
							v-for="(row,i) in form.revenues"
							:key="i"
							class="row g-2 mb-2 align-items-center"
						>
							<div class="col">
								<input v-model="row.label" placeholder="ラベル" class="form-control" />
							</div>
							<div class="col">
								<input
									v-model.number="row.amount"
									type="number"
									min="0"
									placeholder="金額"
									class="form-control"
								/>
							</div>
							<!-- ボタン列 -->
							<div class="col-auto">
								<!-- 1 行目だけ「＋」、それ以外は「－」 -->
								<button
									v-if="i === 0"
									class=""
									@click="form.revenues.push({ label: '', amount: 0 })"
								>
									<span class="material-symbols-outlined">
									add_circle
									</span>
								</button>
								<button
									v-else
									class=""
									@click="form.revenues.splice(i, 1)"
								>
									<span class="material-symbols-outlined">
									do_not_disturb_on
									</span>
								</button>
							</div>
						</div>
					</div>
				</div>

				<!-- ◆ マニュアル経費 ◆ -->
				<div class="area">
					<div class="h5">マニュアル経費</div>
					<div class="wrap">
						<div
							v-for="(row,i) in form.expenses"
							:key="i"
							class="row g-2 mb-2 align-items-center"
						>
							<div class="col">
								<input v-model="row.label" placeholder="ラベル" class="form-control" />
							</div>
							<div class="col">
								<input
									v-model.number="row.amount"
									type="number"
									min="0"
									placeholder="金額"
									class="form-control"
								/>
							</div>
							<!-- ボタン列 -->
							<div class="col-auto">
								<button
									v-if="i === 0"
									class=""
									@click="form.expenses.push({ label: '', amount: 0 })"
								>
									<span class="material-symbols-outlined">
									add_circle
									</span>
								</button>
								<button
									v-else
									class=""
									@click="form.expenses.splice(i, 1)"
								>
									<span class="material-symbols-outlined">
									do_not_disturb_on
									</span>
								</button>
							</div>
						</div>
					</div>
				</div>

				<!-- 延長 -->
				<div class="area">
					<div class="h5">延長</div>
					<div class="btn-group" role="group">
						<input type="radio" class="btn-check" id="ext0" value="0"
							v-model.number="form.extend_blocks">
						<label class="btn btn-outline-secondary" for="ext0">なし</label>

						<template v-for="b in [1,2,3]" :key="b">
						<input type="radio" class="btn-check"
								:id="`ext${b}`" :value="b"
								v-model.number="form.extend_blocks">
						<label class="btn btn-outline-primary"
								:for="`ext${b}`">{{ b*30 }} 分</label>
						</template>
					</div>
				</div>

			</div><!-- form-area__wrap -->


			<!-- 見積 -->
			<div class="summary-area">
				<div class="alert alert-warning">
					<span class="head">小計</span>
					<span class="price">{{ price.toLocaleString() }}</span>
				</div>
			</div>

			<div class="receive-area">
				<div class="wrap">

					<!-- カード -->
					<div class="area">
					<div class="h5">カード</div>
					<input
						type="number" min="0"
						v-model.number="form.pay_card"
						class="form-control"
					/>
					</div>

					<!-- ▼ 現金（自動計算・上書き可） -->
					<div class="area">
					<div class="h5">現金</div>
					<span class="form-control-plaintext fw-bold">
						{{ form.pay_cash.toLocaleString() }} 円
					</span>
					</div>


					<!-- ▼ 受取金 -->
					<div class="area">
						<div class="h5">受取金</div>
						<input
							type="number" min="0"
							v-model.number="form.received_amount"
							class="form-control"
							@input="isRecvManual = true"
						/>
					</div>

					<!-- 釣り銭 -->
					<div class="area">
						<div class="h5">お釣り</div>
						<input
							type="number" min="0"
							v-model.number="form.change_amount"
							class="form-control"
							:placeholder="suggestedChange.toLocaleString()"
						/>
					</div>

				</div>

				<!-- ▼ バリデーションメッセージ -->
				<!-- <div v-if="paymentDiff !== 0" class="mt-2">
					<div
					:class="[
						'alert',
						paymentDiff > 0 ? 'alert-danger' : 'alert-warning'
					]"
					>
					受取合計と小計に
					{{ Math.abs(paymentDiff).toLocaleString() }} 円の
					{{ paymentDiff > 0 ? '超過' : '不足' }}があります
					</div>
				</div> -->
			</div>


			<div class="save-area">
				<button class="btn btn-primary" @click="save">保存</button>
			</div>
		</div><!-- form-area -->
	</div><!-- from-admin__wrap -->
	</div><!-- form-admin -->


</div>
</template>

