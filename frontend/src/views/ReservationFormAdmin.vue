<script setup>
/* =============================================================== *
 *  ReservationFormAdmin.vue  –  管理者予約フォーム
 *  ・店舗選択後に [キャスト検索] ボタンを押すと所属キャストを取得
 *  ・取得したキャストは ReservationCastSelector.vue で選択
 * =============================================================== */
import { ref, computed, onMounted, watch, toRef } from 'vue'
import { asyncComputed }            from '@vueuse/core'
import { useRoute, useRouter }      from 'vue-router'
import debounce                     from 'lodash.debounce'
import ReservationCastSelector      from '@/components/ReservationCastSelector.vue'   // ★追加
import {
  getStores, getCustomers, getDrivers, getCourses,
  getOptions, getCastProfiles, getPrice,
  searchCustomers, createCustomer,
  createReservation, updateReservation, getReservation,
  getLatestReservation, getCustomerAddresses, createCustomerAddress
} from '@/api'

/* ---------- 受け取る prop ---------- */
const props = defineProps({
  reservationId: { type: [Number, String], default: null },
  inModal      : { type: Boolean,            default: false }  // ★ 追加
})

const emit = defineEmits(['saved'])

/* ---------- 基本 ---------- */
const route   = useRoute()
const router  = useRouter()
const latest = ref(null)
const currentId = computed(() =>
  props.reservationId ?? route.params.id ?? null
)
const isEdit = computed(() => !!currentId.value)

/* ---------- 読み取り専用 ---------- */
const rsv = ref({ received_amount: 0 })

/* ---------- フォーム値 ---------- */
const form = ref({
  reservation_type: 'normal',
  stores:          [],
  cast_profiles:   [],
  start_at:        '',
  course:          '',
  driver_PU:       '',          // ★Pick-Up 用
  driver_DO:       '',
  customer:        '',
  deposited_amount: 0,
  /* 支払い */
  pay_card: 0,
  pay_cash: 0,
  /* マニュアル売上 / 経費（複数行可）*/
  revenues: [ { label:'', amount:0 } ],
  expenses: [ { label:'', amount:0 } ],
})

/* ---------- マスタ ---------- */
const opts = ref({
  stores:    [], customers: [], drivers: [],
  courses:   [], options:   []
})

 /* --- 店舗ごとのキャストをキャッシュ --- */
	const castsByStore  = ref({})          // 検索結果キャッシュ
	const searchStores  = ref([])          // 「検索確定」した店舗
	/* 選択中キャストが所属外なら外す */
	/* ❶ ここで **グローバル** に visibleCasts を定義しておく */
	const visibleCasts = computed(() =>
	  Object.keys(castsByStore.value)
	        .flatMap(id => castsByStore.value[id] || [])
	)
 

/* ---------- キャストを検索（ボタン押下） ---------- */
async function fetchCasts () {

	searchStores.value = [...form.value.stores]
	castsByStore.value = {};

	/* ――― ここから新ロジック ――― */
	// ① まず API クエリパラメータを組み立てる
	const params = {}
		if (form.value.stores.length) params.store = form.value.stores.join(',');

	// ② 取得して “all” キーにまとめてキャッシュ
	castsByStore.value = {
	  all: await getCastProfiles(params)     // API 側は複合クエリ対応済み前提
	};
  /* 選択中キャストが所属外なら外す */
  form.value.cast_profiles = form.value.cast_profiles
    .filter(id => visibleCasts.value.some(c => c.id === id))
}

/* ---------- マスタ取得 ---------- */
async function fetchMasters () {
  const [stores, customers, drivers, courses, options] = await Promise.all([
    getStores(), getCustomers(), getDrivers(), getCourses(), getOptions()
  ])
  opts.value = { stores, customers, drivers, courses, options }

}

/* ---------- 既存予約読み込み（編集時） ---------- */
async function fetchReservation () {
  if (!isEdit.value) return
  const res = await getReservation(currentId.value)
  latest.value = await getLatestReservation(res.customer)
  rsv.value = res
  Object.assign(form.value, {
    stores          : res.store ? [res.store] : [],
    cast_profiles   : [],
    start_at        : res.start_at.slice(0,16),
    course          : res.casts[0]?.course ?? '',
	driver_PU       : res.drivers?.find(d => d.role === 'PU')?.driver || '',
	driver_DO       : res.drivers?.find(d => d.role === 'DO')?.driver || '',
    customer        : res.customer,
    deposited_amount: res.deposited_amount ?? 0,
  reservation_type: res.reservation_type,
  pay_card : res.payments.find(p => p.method === 'card')?.amount || 0,
  pay_cash : res.payments.find(p => p.method === 'cash')?.amount || 0,
  })

  form.value.revenues = res.manual_entries
    .filter(e => e.entry_type === 'revenue')
    .map(e => ({ label:e.label, amount:e.amount })) || [{label:'',amount:0}]
  form.value.expenses = res.manual_entries
    .filter(e => e.entry_type === 'expense')
    .map(e => ({ label:e.label, amount:e.amount })) || [{label:'',amount:0}]

  // 顧客住所帳
  addresses.value = await getCustomerAddresses(res.customer)
  if (res.address_book) {
    selectedAddress.value = res.address_book
  } else if (res.address_text) {
    selectedAddress.value = '__new__'
    newAddress.value      = { label: '', address_text: res.address_text }
  }

  selectedOptions.value = res.charges
    .filter(c => c.kind === 'OPTION')
    .map(c => c.option)

	await fetchCasts()
	// API は cast_profile を “数値” で返すので、そのままセット
	form.value.cast_profiles = res.casts.map(c => 
		typeof c.cast_profile === 'object' ? c.cast_profile.id : c.cast_profile
	)
}

/* ---------- オプション選択 ---------- */
const selectedOptions = ref([])

/* ---------- 顧客検索（省略: 以前と同じ） ---------- */
const phone	  = ref('')
const candidates = ref([])
const showList   = ref(false)
const fetchCandidates = debounce(async () => {
  if (phone.value.length < 3) { showList.value = false; return }
  candidates.value = await searchCustomers(phone.value)
  showList.value   = candidates.value.length > 0
}, 400)
const selectedCustomer = computed(
  () => opts.value.customers.find(c => c.id === form.value.customer) || null
)
function choose (c) {
  if (!opts.value.customers.some(x => x.id === c.id)) opts.value.customers.push(c)
  form.value.customer = c.id
  phone.value   = c.phone
  showList.value= false
}
async function registerNew () {
  const name = prompt('顧客名'); if (!name) return
  const address = prompt('住所') || ''
  const newCust = await createCustomer({ name, phone: phone.value, address })
  choose(newCust)
}
function clearCustomer () { form.value.customer=''; phone.value=''; showList.value=false }


// タブインデント！
const addresses			= ref([])		// 一覧
const selectedAddress	= ref('')		// 選択中 id or "__new__"
const newAddress		= ref({			// 新規入力用
	label: '',
	address_text: ''
})

// 顧客が決まったら住所一覧を取得
watch(() => form.value.customer, async id => {
	if (!id) {
		addresses.value = []
		selectedAddress.value = ''
		latest.value = null 
		return
	}
	addresses.value = await getCustomerAddresses(id)
	latest.value = await getLatestReservation(id)
})

/* ---------- 料金計算（省略: 以前と同じ） ---------- */
/* 1. キャスト×コース基本料金（非同期計算） */
const castPriceSum = asyncComputed(
  async () => {

    if (!form.value.course || !form.value.cast_profiles.length) return 0;

	  /* どんな形で来ても最終的に純粋な ID 配列にする */
	  const ids = form.value.cast_profiles
	    .map(c =>
	      typeof c === 'number'         ? c :
	      typeof c === 'object'         ? (c.cast_profile ?? c.id) :
	      null
	    )
    .filter(Boolean);               // undefined / null を除外

     /* 例）バックエンドで一括見積 API がある場合 */
     return await getPrice({
      course        : form.value.course,
      cast_profile  : ids,
     })
	},
	0,                                   // 初期値
	{ lazy:false }                       // ← これで必ず 1 回目が走る
);

/* 2. オプション料金 */
const optionPriceSum = computed(() =>
  selectedOptions.value
	.map(id => opts.value.options.find(o => o.id === id)?.default_price ?? 0)
	.reduce((a,b)=>a+b, 0)
)

/* 3. 手書き・延長など自由枠 */
const revenueSum = computed(() =>
  form.value.revenues.reduce((t, r) => t + (+r.amount || 0), 0)
)

  /* ---------- 延長料金系 ---------- */
const extendUnit = computed(() => {
  const leader = visibleCasts.value.find(c => c.id === form.value.cast_profiles[0])
  return leader?.extend_price_30 || 0     // ← rank をたどらず 1 発
})

/* 1. 延長料金 (30-min ブロック × 単価) */
const extendPriceSum = computed(() =>
	(form.value.extend_blocks || 0) * extendUnit.value
)

/* 4. 合計 */
const price = computed(() =>
  castPriceSum.value + optionPriceSum.value + revenueSum.value + extendPriceSum.value
)

/* ---------- 初期ロード ---------- */
onMounted(async () => {
  await fetchMasters();
  await fetchReservation();
  if (!isEdit) await fetchCasts()   // ← 新規時は全店取得
});

/** ② モーダルを開いたまま別バーをクリックしたとき再取得 */
watch(
   () => props.reservationId,
   fetchReservation
)

/* ---------- 保存（省略: 以前と同じ） ---------- */
// ───────── まるごと置き換え ─────────
async function save () {
  /* ---------- 前準備 ---------- */
  const minutes =
    opts.value.courses.find(c => c.id === form.value.course)?.minutes ?? 0

  const toId = v => (v && typeof v === 'object') ? v.id : v
  const castIdOf = c =>
        typeof c === 'number'                         ? c :
        typeof c === 'object' && 'cast_profile' in c ? c.cast_profile :
        typeof c === 'object' && 'id' in c            ? c.id :
        null
  const castIds = form.value.cast_profiles
        .map(castIdOf)
        .filter(Boolean)

  /* ---------- store 決定ロジック & バリデーション ---------- */
  const castStores = castIds
    .map(id => visibleCasts.value.find(c => c.id === id))
    .map(c => c?.store ?? c?.store_id ?? null)
    .filter(Boolean)

  let storeId = form.value.stores[0] ?? castStores[0] ?? null
  const uniqueStores = [...new Set(castStores)]

  if (!form.value.stores.length && uniqueStores.length > 1) {
    alert('異なる店舗のキャストが混在しています。店舗を選択してください'); return
  }
  if (form.value.stores.length && uniqueStores.some(s => s !== storeId)) {
    alert('選択した店舗とキャストの店舗が一致しません'); return
  }
  if (!storeId) {
    alert('店舗またはキャストを選択してください'); return
  }



  /* ---------- payload ---------- */

	const payments = [
		...(form.value.pay_card ? [{ method:'card', amount:Number(form.value.pay_card) }] : []),
		...(form.value.pay_cash ? [{ method:'cash', amount:Number(form.value.pay_cash) }] : []),
	]
	const manual_entries = [
		...form.value.revenues
			.filter(e => e.label && e.amount)
			.map(e => ({ entry_type:'revenue', label:e.label, amount:Number(e.amount) })),
		...form.value.expenses
			.filter(e => e.label && e.amount)
			.map(e => ({ entry_type:'expense', label:e.label, amount:Number(e.amount) })),
	]

	const payload = {
		reservation_type: form.value.reservation_type,
		store : storeId,
		drivers: [
		...(form.value.driver_PU ? [{ role:'PU', driver:toId(form.value.driver_PU) }] : []),
		...(form.value.driver_DO ? [{ role:'DO', driver:toId(form.value.driver_DO) }] : []),
		],
		reservation_type : form.value.reservation_type,
		store            : storeId,
		customer        : form.value.customer || null,
		start_at        : new Date(form.value.start_at).toISOString(),
		total_time      : minutes,
		deposited_amount: form.value.deposited_amount,
		casts: castIds.map(id => ({ cast_profile:id, course:form.value.course })),
		payments,
		manual_entries,
		extend_blocks: form.value.extend_blocks || 0,
		total_time: minutes + (form.value.extend_blocks||0)*30,
	}

  /* ---------- 住所帳 ---------- */
  if (selectedAddress.value === '__new__') {
    if (!newAddress.value.address_text.trim()) {
      alert('住所を入力してください'); return
    }
    const created = await createCustomerAddress(form.value.customer, newAddress.value)
    payload.address_book = created.id
  } else {
    payload.address_book = selectedAddress.value || null
  }

  /* ---------- 保存 ---------- */
  try {
    // ---- 登録 or 更新 ----------------------------------
    const id = isEdit.value
      ? (await updateReservation(currentId.value, payload), currentId.value)
      : (await createReservation(payload)).id            // 新規

    /* 親（モーダル側 or 画面側）に結果を通知 */
    emit('saved', { id })          

    /* モーダルで使われている時はここで終了 ----------------*/
    if (props.inModal) return

    /* 通常画面のときだけ遷移させる -------------------------*/
    // 例: 詳細画面へ
    await router.push(`/reservations/${id}`)
    // もし「一覧で十分」なら ↓
    // await router.push('/reservations')

  } catch (e) {
    console.error(e.response?.data)
    alert(e.response?.data?.detail || 'バリデーションエラー')
  }	

}


if (import.meta.env.DEV) {
  Object.assign(window, {
    debug: { form, visibleCasts, price, castPriceSum }
  })
}
</script>

<template>
<div class="form form-admin container py-5">
  <h1 class="h3 mb-4">
    管理者用ページ&nbsp;
    {{ isEdit ? `予約 #${route.params.id} 編集` : '新規予約' }}
  </h1>


	<!-- 顧客（電話検索） -->
	<div class="my-5 customer">
	  <div class="wrap d-flex gap-4">
		<div class="col-8 search">
			<!-- 入力 -->
			<input v-if="!selectedCustomer" v-model="phone" @input="fetchCandidates"
				  class="form-control" placeholder="090…" />

			<!-- 候補 -->
			<ul v-if="showList" class="d-flex gap-4 mt-4">
			  <li v-for="c in candidates" :key="c.id"
				  class="btn btn-outline-primary"
				  @click="choose(c)">
				{{ c.name }} / {{ c.phone }}
			  </li>
			</ul>

			<!-- 選択済み表示 -->
			<div v-if="selectedCustomer" class="selected p-2 bg-white rounded d-flex align-items-center justify-content-between">
			  <div class="wrap">
				{{ selectedCustomer.name }}（{{ selectedCustomer.phone }}）
			  </div>
			  <button class="btn btn-outline-secondary" @click="clearCustomer">
				変更
			  </button>
			</div>

			<!-- 直近カード -->
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
							<span>
								{{ new Date(latest.start_at).toLocaleString() }} / {{ latest.store_name }}
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
							<li v-for="o in latest.options" :key="o.option_id" class="badge bg-secondary">
								{{ o.name }}
							</li>
						</ul>
						<div class="items">
							<span>金額: {{ latest.expected_amount.toLocaleString() }} 円</span>
						</div>

					</div>
				</div>
			  </div>
			</div>
		</div>
		<div class="col-4">
		  <button class="btn btn-primary w-100" @click="registerNew">＋ 新規顧客を登録</button>
		</div>
	  </div>

	</div>

  <!-- ◆ 店舗選択 ◆ -->
   <div class="cast-search">

	<div class="mb-3 d-flex justify-content-center flex-column gap-4">
		<div class="search-area  d-flex gap-4 flex-column">
			<div class="box d-flex gap-4">
				<template v-for="s in opts.stores" :key="s.id">
				<input class="btn-check" type="checkbox"
						:id="`store-${s.id}`" v-model="form.stores" :value="s.id">
				<label class="btn btn-outline-primary me-2 mb-2"
						:for="`store-${s.id}`"
						:class="{ active: form.stores.includes(s.id) }">
					{{ s.name }}
				</label>
				</template>
			</div>
			<div class="box d-flex gap-4">
				<div class="btn btn-outline-primary disabled">綺麗系</div>
				<div class="btn btn-outline-primary disabled">可愛い系</div>
				<div class="btn btn-outline-primary disabled">モデル</div>
			</div>
			<div class="box d-flex gap-4">
				<div class="btn btn-outline-primary disabled">Aカップ</div>
				<div class="btn btn-outline-primary disabled">Bカップ</div>
				<div class="btn btn-outline-primary disabled">Cカップ</div>
				<div class="btn btn-outline-primary disabled">Dカップ</div>
				<div class="btn btn-outline-primary disabled">Eカップ</div>
			</div>

		</div>
		<!-- ▼ キャスト検索ボタン -->
		<button class="btn btn-sm btn-success ms-2"
				:disabled="false"
				@click="fetchCasts">
		キャスト検索
		</button>
	</div>

   </div>

	<div class="contents">
		  <!-- ◆ キャスト選択 ◆ -->
  <div class="area">
    <div class="h5">キャスト</div>
	<div class="bg-white p-4">
		<ReservationCastSelector
		:casts="visibleCasts"
		v-model:modelValue="form.cast_profiles"
		/>
	</div>
  </div>


	<!-- タブインデント！ -->
	 <div class="area">
		<div class="h5">送迎場所</div>
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


	<!-- 開始日時 -->
	<div class="area">
	  <div class="h5">開始日時</div>
	  <input type="datetime-local" v-model="form.start_at" class="form-control">
	</div>

	<!-- ★ select を削除してボタン型ラジオへ -->
	<div class="area">
	  <div class="h5">コース</div>
	  <div class="d-flex flex-wrap gap-3" role="group" aria-label="Courses">
		<template v-for="c in opts.courses" :key="c.id">
		  <!-- hidden radio -->
		  <input  class="btn-check" type="radio"
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
	<!-- オプション -->
	<div class="area">
	  <div class="h5">オプション</div>

	  <!-- 見た目をそろえるため flex+gap  -->
	  <div class="d-flex flex-wrap gap-3" role="group" aria-label="Options">

		<template v-for="o in opts.options" :key="o.id">
		  <!-- hidden checkbox -->
		  <input  class="btn-check" type="checkbox"
				  :id="`opt-${o.id}`"
				  v-model="selectedOptions"
				  :value="o.id" autocomplete="off">

		  <!-- 表示用ボタン -->
		  <label class="btn btn-outline-primary"
				:class="{ active: selectedOptions.includes(o.id) }"
				:for="`opt-${o.id}`">

			{{ o.name }}
			<small class="d-block fw-normal">
			  ¥{{ o.default_price.toLocaleString() }}
			</small>
		  </label>
		</template>

	  </div>
	</div>

	<!-- ドライバー -->
	<!-- ▼ ドライバー選択 -->
	<div class="area">
	<div class="h5">ドライバー (Pick-Up)</div>
	<div class="d-flex flex-wrap gap-3" role="group" aria-label="Drivers-PU">
		<input  class="btn-check" type="radio" id="driverPU-null"
				value="" v-model.number="form.driver_PU">
		<label class="btn btn-outline-secondary"
			:class="{ active: form.driver_PU === '' }"
			for="driverPU-null">未指定</label>

		<template v-for="d in opts.drivers" :key="d.id">
		<input  class="btn-check" type="radio"
				:id="`driverPU-${d.id}`"
				v-model.number="form.driver_PU"
				:value="d.id">
		<label class="btn btn-outline-primary"
				:class="{ active: form.driver_PU === d.id }"
				:for="`driverPU-${d.id}`">{{ d.name }}</label>
		</template>
	</div>
	</div>

	<div class="area">
	<div class="h5">ドライバー (Drop-Off)</div>
	<div class="d-flex flex-wrap gap-3" role="group" aria-label="Drivers-DO">
		<input  class="btn-check" type="radio" id="driverDO-null"
				value="" v-model.number="form.driver_DO">
		<label class="btn btn-outline-secondary"
			:class="{ active: form.driver_DO === '' }"
			for="driverDO-null">未指定</label>

		<template v-for="d in opts.drivers" :key="d.id">
		<input  class="btn-check" type="radio"
				:id="`driverDO-${d.id}`"
				v-model.number="form.driver_DO"
				:value="d.id">
		<label class="btn btn-outline-primary"
				:class="{ active: form.driver_DO === d.id }"
				:for="`driverDO-${d.id}`">{{ d.name }}</label>
		</template>
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


	<!-- ◆ 支払い方法 ◆ -->
	<!-- <div class="area">
	<div class="h5">支払い</div>
	<div class="row g-3">
		<div class="col-md-3">
		<label class="form-label">カード</label>
		<input type="number" class="form-control"
				v-model.number="form.pay_card" min="0" />
		</div>
		<div class="col-md-3">
		<label class="form-label">現金</label>
		<input type="number" class="form-control"
				v-model.number="form.pay_cash" min="0" />
		</div>
	</div>
	</div> -->


	<!-- ◆ マニュアル売上 ◆ -->
	<div class="area">
	<div class="h5">マニュアル売上</div>
	<div v-for="(row,i) in form.revenues" :key="i" class="row g-2 mb-2">
		<div class="col">
		<input v-model="row.label" placeholder="ラベル" class="form-control" />
		</div>
		<div class="col">
		<input v-model.number="row.amount" type="number" min="0"
				placeholder="金額" class="form-control" />
		</div>
		<div class="col-auto">
		<button class="btn btn-outline-danger"
				@click="form.revenues.splice(i,1)"
				v-if="form.revenues.length>1">－</button>
		</div>
	</div>
	<button class="btn btn-sm btn-outline-primary"
			@click="form.revenues.push({label:'',amount:0})">＋ 行を追加</button>
	</div>

	<!-- ◆ マニュアル経費 ◆ -->
	<div class="area">
	<div class="h5">マニュアル経費</div>
	<div v-for="(row,i) in form.expenses" :key="i" class="row g-2 mb-2">
		<div class="col">
		<input v-model="row.label" placeholder="ラベル" class="form-control" />
		</div>
		<div class="col">
		<input v-model.number="row.amount" type="number" min="0"
				placeholder="金額" class="form-control" />
		</div>
		<div class="col-auto">
		<button class="btn btn-outline-danger"
				@click="form.expenses.splice(i,1)"
				v-if="form.expenses.length>1">－</button>
		</div>
	</div>
	<button class="btn btn-sm btn-outline-primary"
			@click="form.expenses.push({label:'',amount:0})">＋ 行を追加</button>
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

	<!-- 見積 -->
	<div class="area">
	  <div class="alert alert-warning">
		現在の見積 <strong>{{ price.toLocaleString() }}</strong> 円
	  </div>
	</div>



	<!-- テンプレート：受取と入金の 2 つ表示 -->
	<div class="area">
		<div class="h5">受取金額</div>
		<input type="number" class="form-control" v-model.number="rsv.received_amount" disabled />
		</div>
		<div class="area">
		<div class="h5">入金額</div>
		<input type="number" class="form-control" v-model.number="form.deposited_amount" />
		</div>

		<div class="areatext-end">
		<button class="btn btn-primary" @click="save">保存</button>
		</div>
	</div>







</div>
</template>

