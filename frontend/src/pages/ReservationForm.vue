<template>
	<div class="reservation__create">
	  <h2>新規予約</h2>
  
	  <!-- 予約名 (customer_name) -->
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
		  <option v-for="store in storeOptions" :key="store.id" :value="store.id">
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
  
	  <!-- 予約開始時間 (start_time) -->
	  <div>
		<label>開始時刻</label>
		<!-- 必須にしたければ required をつける。秒まで入力が必要な場合、注意。 -->
		<input 
		  type="datetime-local" 
		  v-model="formData.start_time" 
		  required
		/>
	  </div>
  
	  <!-- 予約時間(分) (time_minutes) -->
	  <div>
		<label>予約時間(分)</label>
		<input 
		  type="number" 
		  v-model.number="formData.time_minutes" 
		/>
	  </div>
  
	  <!-- メニュー (チェックボックス) -->
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
  
	  <!-- 追加オプション (入会金、写真指名など) -->
	  <div class="area checkbox">
		<div class="head">その他</div>
		<div class="value">
		  <div>
			<input 
			  type="checkbox" 
			  v-model="formData.enrollment_fee" 
			/>
			入会金
		  </div>
		  <div>
			<input 
			  type="checkbox" 
			  v-model="formData.enrollment_fee_discounted" 
			/>
			入会金0円
		  </div>
		  <div>
			<input 
			  type="checkbox" 
			  v-model="formData.photo_nomination_fee" 
			/>
			写真指名
		  </div>
		  <div>
			<input 
			  type="checkbox" 
			  v-model="formData.photo_nomination_fee_discounted" 
			/>
			写真指名0円
		  </div>
		  <div>
			<input 
			  type="checkbox" 
			  v-model="formData.regular_nomination_fee" 
			/>
			本指名
		  </div>
		  <div>
			<input 
			  type="checkbox" 
			  v-model="formData.regular_nomination_fee_discounted" 
			/>
			本指名割引
		  </div>
		</div>
	  </div>
  
	  <!-- 予約金額表示 -->
	  <div>
		<label>予約金額</label>
		{{ formData.reservation_amount }}
	  </div>
  
	  <!-- 計算ボタン -->
	  <button @click="calcReservation">計算</button>
  
	  <!-- 作成ボタン (POST) -->
	  <button @click="createReservation">作成</button>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import api from '@/api' // Axiosインスタンス等
  
  const router = useRouter()
  
  // =========== 各種選択肢のリスト ===========
  const storeOptions = ref([])       // 店舗
  const storeUserOptions = ref([])   // 店舗に紐づくキャスト (StoreUser)
  const driverOptions = ref([])      // ドライバー
  const menuOptions = ref([])        // メニュー
  const rankOptions = ref([])        // ランク (price_60..)
  
  // =========== 店舗を選んだときに使う ===========
  const selectedStoreId = ref(null)
  
  // =========== フォームデータ ===========
  const formData = ref({
	customer_name: '',        // 予約名
	store_user: null,         // 選択されたキャスト(StoreUser)のID
	driver: null,             // ドライバーID
	start_time: '',           // 予約開始時刻
	time_minutes: 60,         // 予約時間
	menus: [],                // 選択メニューIDの配列
	enrollment_fee: false,
	enrollment_fee_discounted: false,
	photo_nomination_fee: false,
	photo_nomination_fee_discounted: false,
	regular_nomination_fee: false,
	regular_nomination_fee_discounted: false,
	reservation_amount: 0,    // 計算結果
  })
  
  // =========== onMountedでAPIを取得 ===========
  onMounted(async () => {
	await fetchRanks()
	await fetchStores()
	await fetchMenus()
	await fetchDrivers()
  })
  
  // ランク一覧
  async function fetchRanks() {
	try {
	  const { data } = await api.get('/accounts/ranks/')
	  rankOptions.value = data
	} catch (err) {
	  console.error('ランク一覧取得失敗', err)
	}
  }
  // 店舗一覧
  async function fetchStores() {
	try {
	  const { data } = await api.get('/accounts/stores/')
	  storeOptions.value = data
	} catch (e) {
	  console.error('店舗一覧取得失敗', e)
	}
  }
  // メニュー一覧
  async function fetchMenus() {
	try {
	  const { data } = await api.get('/reservations/menus/')
	  menuOptions.value = data
	} catch (e) {
	  console.error('メニュー一覧取得失敗', e)
	}
  }
  // ドライバー一覧
  async function fetchDrivers() {
	try {
	  const { data } = await api.get('/accounts/users/?role=driver')
	  driverOptions.value = data
	} catch (e) {
	  console.error('ドライバー一覧取得失敗', e)
	}
  }
  
  // 店舗が選択された時に呼び出し
  async function fetchStoreUsers() {
	if (!selectedStoreId.value) {
	  storeUserOptions.value = []
	  formData.value.store_user = null
	  return
	}
	try {
	  const { data } = await api.get(`/accounts/store-users/?store=${selectedStoreId.value}`)
	  storeUserOptions.value = data
	  formData.value.store_user = null
	} catch (e) {
	  console.error('StoreUser一覧取得失敗', e)
	}
  }
  
  // =========== 計算処理 ===========
  function calcReservation() {
	console.log("calcReservation called!")
	let total = 0
  
	// メニュー加算
	formData.value.menus.forEach(menuId => {
	  const item = menuOptions.value.find(m => m.id === menuId)
	  if (item) total += Number(item.price) || 0
	})
  
	// 入会金
	if (formData.value.enrollment_fee) total += 5000
	// 写真指名
	if (formData.value.photo_nomination_fee) total += 2000
  
	// ランクを加味するならここで storeUserOptions と rankOptions を参照
	const chosenSU = storeUserOptions.value.find(su => su.id === formData.value.store_user)
	if (chosenSU) {
	  const chosenRank = rankOptions.value.find(r => r.id === chosenSU.rank_id)
	  if (chosenRank) {
		// 例: 時間別料金 (price_60 etc.)
		const t = formData.value.time_minutes
		if (t === 60) total += chosenRank.price_60
		else if (t === 75) total += chosenRank.price_75
		// ...以下省略
  
		// 星数
		const starCount = chosenSU.star_count || 0
		total += starCount * chosenRank.plus_per_star
	  }
	}
  
	formData.value.reservation_amount = total
	console.log("計算結果:", total)
  }
  
  // =========== 予約作成(POST) ===========
  async function createReservation() {
	try {
	  const payload = { ...formData.value }
	  console.log('送信payload:', payload)
	  await api.post('/reservations/', payload)
	  alert('予約を作成しました')
	  router.push('/reservations')  // 一覧ページへ
	} catch (err) {
	  console.error('予約作成失敗', err)
	  alert('作成に失敗しました')
	}
  }
  </script>
  