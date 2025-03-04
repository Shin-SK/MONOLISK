<template>
	<div class="reservation__form">
	  <h2>予約編集</h2>
  
	  <!-- ===== 予約名 (customer_name) ===== -->
	  <div>
		<label>予約名</label>
		<input 
		  type="text" 
		  v-model="formData.customer_name" 
		  placeholder="予約名" 
		/>
	  </div>
  
	  <!-- 店舗選択 -->
	  <div>
		<label>店舗</label>
		<select v-model="selectedStoreId" @change="fetchStoreUsers">
		  <option value="" disabled>--- 店舗を選択してください ---</option>
		  <option 
			v-for="store in storeOptions" 
			:key="store.id" 
			:value="store.id"
		  >
			{{ store.name }}
		  </option>
		</select>
	  </div>
  
	  <!-- キャスト(StoreUser)選択 -->
	  <div v-if="storeUserOptions.length">
		<label>キャスト (StoreUser)</label>
		<select v-model="formData.store_user">
		  <option value="" disabled>--- キャストを選択してください ---</option>
		  <option
			v-for="su in storeUserOptions"
			:key="su.id"
			:value="su.id"
		  >
			{{ su.full_name }} ({{ su.nickname }}) 
			- ランク: {{ su.rank_name }} ☆{{ su.star_count }}
		  </option>
		</select>
	  </div>
  
	  <!-- ドライバー選択 -->
	  <div>
		<label>ドライバー</label>
		<select v-model="formData.driver">
		  <option value="" disabled>--- ドライバーを選択してください ---</option>
		  <option
			v-for="drv in driverOptions"
			:key="drv.id"
			:value="drv.id"
		  >
			{{ drv.full_name }}
		  </option>
		</select>
	  </div>
  
	  <!-- 予約開始時間 -->
	  <div>
		<label>開始時刻</label>
		<input 
		  type="datetime-local" 
		  v-model="formData.start_time" 
		/>
	  </div>
  
	  <!-- 予約時間(分) -->
	  <div>
		<label>予約時間(分)</label>
		<input 
		  type="number" 
		  v-model.number="formData.time_minutes" 
		/>
	  </div>
  
	  <!-- メニュー一覧 (チェックボックス) -->
	  <div>
		<label>メニュー</label>
		<div 
		  v-for="menu in menuOptions" 
		  :key="menu.id"
		>
		  <input
			type="checkbox"
			:value="menu.id"
			v-model="formData.menus"
		  />
		  {{ menu.name }} ({{ menu.price }}円)
		</div>
	  </div>
  
	  <!-- 追加オプション (入会金, 写真指名など) -->
	  <div class="area checkbox">
		<div class="head">その他</div>
		<div class="value">
		  <div>
			<input type="checkbox" v-model="formData.enrollment_fee" />
			入会金
		  </div>
		  <div>
			<input type="checkbox" v-model="formData.enrollment_fee_discounted" />
			入会金0円
		  </div>
		  <div>
			<input type="checkbox" v-model="formData.photo_nomination_fee" />
			写真指名
		  </div>
		  <div>
			<input type="checkbox" v-model="formData.photo_nomination_fee_discounted" />
			写真指名0円
		  </div>
		  <div>
			<input type="checkbox" v-model="formData.regular_nomination_fee" />
			本指名
		  </div>
		  <div>
			<input type="checkbox" v-model="formData.regular_nomination_fee_discounted" />
			本指名割引
		  </div>
		</div>
	  </div>
  
	  <!-- キャスト受取金 / ドライバー受取金 / 店舗受取金 -->
	  <div>
		<label>キャスト受取金</label>
		<input 
		  type="number" 
		  v-model.number="formData.cast_received"
		/>
	  </div>
	  <div>
		<label>ドライバー受取金</label>
		<input 
		  type="number" 
		  v-model.number="formData.driver_received"
		/>
	  </div>
	  <div>
		<label>店舗受取金</label>
		<input 
		  type="number" 
		  v-model.number="formData.store_received"
		/>
	  </div>
  
	  <!-- 予約金額表示 -->
	  <div>
		<label>予約金額</label>
		{{ formData.reservation_amount }}
	  </div>
  
	  <!-- 計算ボタン -->
	  <button @click="calcReservation">計算</button>
  
	  <!-- 更新ボタン -->
	  <button @click="updateReservation">更新</button>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import api from '@/api' // Axios
  
  // ルータ
  const route = useRoute()
  const router = useRouter()
  
  // 予約ID (必須)
  const reservationId = route.params.id || null
  
  // ============ 選択肢リスト ===========
  const storeOptions = ref([])
  const storeUserOptions = ref([])
  const driverOptions = ref([])
  const menuOptions = ref([])
  const rankOptions = ref([])
  
  // 店舗選択時に使う
  const selectedStoreId = ref(null)
  
  // ============ フォームデータ ===========
  const formData = ref({
	customer_name: '',
	store_user: null,
	driver: null,
	start_time: '',
	time_minutes: 60,
	menus: [],
	enrollment_fee: false,
	enrollment_fee_discounted: false,
	photo_nomination_fee: false,
	photo_nomination_fee_discounted: false,
	regular_nomination_fee: false,
	regular_nomination_fee_discounted: false,
	cast_received: 0,
	driver_received: 0,
	store_received: 0,
	reservation_amount: 0
  })
  
  // onMounted: データ取得
  onMounted(async () => {
	// 初期情報
	await fetchRanks()
	await fetchStores()
	await fetchMenus()
	await fetchDrivers()
  
	// 既存予約詳細を読み込む
	if (!reservationId) {
	  alert('予約IDが指定されていません')
	  router.push('/dashboard/reservations')
	  return
	}
	await fetchReservation(reservationId)
  })
  
  // ランク一覧
  async function fetchRanks() {
	const { data } = await api.get('/accounts/ranks/')
	rankOptions.value = data
  }
  
  // 店舗一覧
  async function fetchStores() {
	const { data } = await api.get('/accounts/stores/')
	storeOptions.value = data
  }
  
  // メニュー一覧
  async function fetchMenus() {
	const { data } = await api.get('/reservations/menus/')
	menuOptions.value = data
  }
  
  // ドライバー一覧
  async function fetchDrivers() {
	const { data } = await api.get('/accounts/users/?role=driver')
	driverOptions.value = data
  }
  
  // 店舗が選択されたとき → StoreUserを再取得
  async function fetchStoreUsers() {
	if (!selectedStoreId.value) {
	  storeUserOptions.value = []
	  formData.value.store_user = null
	  return
	}
	const { data } = await api.get(`/accounts/store-users/?store=${selectedStoreId.value}`)
	storeUserOptions.value = data
  
	// もし既にセットされている store_user が新しいリストにない場合はnull化
	if (!data.find(su => su.id === formData.value.store_user)) {
	  formData.value.store_user = null
	}
  }
  
  // 既存予約をGET
  async function fetchReservation(id) {
	try {
	  const { data } = await api.get(`/reservations/${id}/`)
	  // 取得したデータを formData に反映
	  formData.value.customer_name = data.customer_name || ''
	  // start_time は "2025-03-05T21:00:00Z" 形式なら slice(0,16) で
	  if (data.start_time) {
		formData.value.start_time = data.start_time.replace('Z','').slice(0,16)
	  }
	  formData.value.time_minutes = data.time_minutes || 60
	  formData.value.menus = data.menus ? data.menus.map(m => m.id) : []
	  formData.value.enrollment_fee = data.enrollment_fee
	  formData.value.enrollment_fee_discounted = data.enrollment_fee_discounted
	  formData.value.photo_nomination_fee = data.photo_nomination_fee
	  formData.value.photo_nomination_fee_discounted = data.photo_nomination_fee_discounted
	  formData.value.regular_nomination_fee = data.regular_nomination_fee
	  formData.value.regular_nomination_fee_discounted = data.regular_nomination_fee_discounted
  
	  formData.value.cast_received = data.cast_received || 0
	  formData.value.driver_received = data.driver_received || 0
	  formData.value.store_received = data.store_received || 0
	  formData.value.reservation_amount = data.reservation_amount || 0
  
	  // 店舗があれば selectedStoreId にセット
	  if (data.store) {
		selectedStoreId.value = data.store.id
		await fetchStoreUsers()
	  }
	  // store_user (数値ならそのまま)
	  if (data.store_user) {
		formData.value.store_user = data.store_user
	  }
	  // driver
	  if (data.driver) {
		formData.value.driver = data.driver.id
	  }
  
	} catch (err) {
	  console.error('予約詳細取得失敗:', err)
	  alert('存在しない予約IDです')
	  router.push('/dashboard/reservations')
	}
  }
  
  // 計算 (Edit時もロジックはCreateと同じ)
  function calcReservation() {
	let total = 0
  
	// メニュー加算
	formData.value.menus.forEach(mId => {
	  const item = menuOptions.value.find(x => x.id === mId)
	  if (item) total += Number(item.price) || 0
	})
  
	// 入会金など
	if (formData.value.enrollment_fee) total += 5000
	if (formData.value.photo_nomination_fee) total += 2000
  
	// ランク計算
	const chosenSU = storeUserOptions.value.find(su => su.id === formData.value.store_user)
	if (chosenSU) {
	  const chosenRank = rankOptions.value.find(r => r.id === chosenSU.rank_id)
	  if (chosenRank) {
		const t = formData.value.time_minutes
		if (t === 60) total += chosenRank.price_60
		else if (t === 75) total += chosenRank.price_75
		// ... その他
		const starCount = chosenSU.star_count || 0
		total += starCount * chosenRank.plus_per_star
	  }
	}
  
	formData.value.reservation_amount = total
	console.log("計算結果:", total)
  }
  
  // 予約更新
  async function updateReservation() {
	try {
	  const payload = { ...formData.value }
	  console.log('送信payload:', payload)
	  await api.put(`/reservations/${reservationId}/`, payload)
	  alert('予約を更新しました')
	  router.push('/dashboard/reservations')
	} catch (err) {
	  console.error('予約更新失敗:', err)
	  alert('更新に失敗しました')
	}
  }
  </script>
  