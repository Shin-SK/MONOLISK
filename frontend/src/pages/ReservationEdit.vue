<template>
	<div class="reservation__edit">
	  <h2>予約編集</h2>
  
	  <!-- 店舗 (Store) -->
	  <div>
		<label>店舗</label>
		<div v-for="store in storeOptions" :key="store.id">
		  <input
			type="radio"
			v-model="formData.store"
			:value="store.id"
		  />
		  {{ store.name }}
		</div>
	  </div>
  
	  <!-- キャスト (Cast) -->
	  <div>
		<label>キャスト</label>
		<div v-for="castItem in castOptions" :key="castItem.id">
		  <input
			type="radio"
			v-model="formData.cast"
			:value="castItem.id"
		  />
		  <!-- 店舗ごとのnickname一覧を表示する例 -->
		  <span v-if="castItem.stores && castItem.stores.length">
			{{ castItem.stores.map(s => s.nickname).join(' / ') }}
		  </span>
		  <span v-else>{{ castItem.nickname }}</span>
		</div>
	  </div>
  
	  <!-- ドライバー (Driver) -->
	  <div>
		<label>ドライバー</label>
		<div v-for="driver in driverOptions" :key="driver.id">
		  <input
			type="radio"
			v-model="formData.driver"
			:value="driver.id"
		  />
		  {{ driver.full_name }}
		</div>
	  </div>
  
	  <!-- コース (Course) -->
	  <div>
		<label>コース</label>
		<div v-for="courseItem in courseOptions" :key="courseItem.id">
		  <input
			type="radio"
			v-model="formData.course"
			:value="courseItem.id"
		  />
		  {{ courseItem.name }} ({{ courseItem.price }}円)
		</div>
	  </div>
  
	  <!-- メニュー (Menu) -->
	  <div>
		<label>メニュー</label>
		<div v-for="menu in menuOptions" :key="menu.id">
		  <input
			type="checkbox"
			v-model="formData.menus"
			:value="menu.id"
		  />
		  {{ menu.name }} ({{ menu.price }}円)
		</div>
	  </div>
  
	  <!-- 割引 (Discount) -->
	  <div>
		<label>割引</label>
		<div v-for="discount in discountOptions" :key="discount.id">
		  <input
			type="checkbox"
			v-model="formData.discounts"
			:value="discount.id"
		  />
		  {{ discount.name }} ({{ discount.amount }}円引き)
		</div>
	  </div>
  
	  <!-- その他 (入会金, 写真指名, 本指名 など) -->
	  <div>
		<label>その他</label>
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
  
	  <!-- 予約時間 (time_minutes) -->
	  <div>
		<label>予約時間(分)</label>
		<input v-model.number="formData.time_minutes" type="number" />
	  </div>
  
	  <!-- 「計算」ボタン -->
	  <button @click="calcReservation">計算</button>
  
	  <!-- 予約金額 (reservation_amount) -->
	  <div>
		<label>予約金額</label>
		<div>{{ formData.reservation_amount }}円</div>
	  </div>
  
	  <!-- キャスト受取金など (cast_received, driver_received, store_received) -->
	  <div>
		<label>キャスト受取金</label>
		<input v-model.number="formData.cast_received" type="number" />
  
		<label>ドライバー受取金</label>
		<input v-model.number="formData.driver_received" type="number" />
  
		<label>店舗受取金</label>
		<input v-model.number="formData.store_received" type="number" />
	  </div>
  
	  <!-- 更新ボタン -->
	  <button @click="updateReservation">更新</button>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import api from '@/api'
  
  // ルータ
  const router = useRouter()
  const route = useRoute()
  
  // 予約ID（編集用）
  const reservationId = route.params.id || null
  
  // 各種選択肢
  const storeOptions = ref([])
  const castOptions = ref([])
  const driverOptions = ref([])
  const courseOptions = ref([])
  const menuOptions = ref([])
  const discountOptions = ref([])
  
  // フォームデータ
  const formData = ref({
	store: null,
	cast: null,
	driver: null,
	course: null,
	menus: [],
	discounts: [],
	enrollment_fee: false,
	enrollment_fee_discounted: false,
	photo_nomination_fee: false,
	photo_nomination_fee_discounted: false,
	regular_nomination_fee: false,
	regular_nomination_fee_discounted: false,
	time_minutes: 0,
	reservation_amount: 0, // 計算結果を格納
	cast_received: 0,
	driver_received: 0,
	store_received: 0,
	// ほか必要に応じて
  })
  
  // マウント時に初期データを取得
  onMounted(async () => {
	await fetchInitialData()
	if (reservationId) {
	  await fetchReservation()
	}
  })
  
  // 選択肢等の取得
  async function fetchInitialData() {
	try {
	  const [storeRes, driverRes, courseRes, menuRes, discountRes] = await Promise.all([
		api.get('/accounts/stores/'),
		api.get('/accounts/users/?role=driver'),
		api.get('/reservations/courses/'),
		api.get('/reservations/menus/'),
		api.get('/reservations/discounts/')
	  ])
	  storeOptions.value = storeRes.data
	  driverOptions.value = driverRes.data
	  courseOptions.value = courseRes.data
	  menuOptions.value = menuRes.data
	  discountOptions.value = discountRes.data
	} catch (e) {
	  alert('初期データの取得に失敗')
	}
  }
  
  // 予約詳細取得
  async function fetchReservation() {
	try {
	  const { data } = await api.get(`/reservations/${reservationId}/`)
	  // 取得したデータをformDataに反映
	  formData.value.store = data.store ? data.store.id : null
	  formData.value.cast = data.cast ? data.cast.id : null
	  formData.value.driver = data.driver ? data.driver.id : null
	  formData.value.course = data.course ? data.course.id : null
	  formData.value.menus = data.menus ? data.menus.map(m => m.id) : []
	  formData.value.discounts = data.discounts
		? data.discounts.map(d => (typeof d === 'object' ? d.id : d))
		: []
	  formData.value.time_minutes = data.time_minutes || 0
	  formData.value.reservation_amount = data.reservation_amount || 0
	  formData.value.enrollment_fee = data.enrollment_fee
	  formData.value.enrollment_fee_discounted = data.enrollment_fee_discounted
	  formData.value.photo_nomination_fee = data.photo_nomination_fee
	  formData.value.photo_nomination_fee_discounted = data.photo_nomination_fee_discounted
	  formData.value.regular_nomination_fee = data.regular_nomination_fee
	  formData.value.regular_nomination_fee_discounted = data.regular_nomination_fee_discounted
  
	  formData.value.cast_received = data.cast_received || 0
	  formData.value.driver_received = data.driver_received || 0
	  formData.value.store_received = data.store_received || 0
  
	  // 店舗に応じてキャスト一覧を動的取得する例 (必要なら)
	  if (formData.value.store) {
		await handleStoreChange()
	  }
	} catch (e) {
	  alert('予約詳細の取得に失敗しました')
	}
  }
  
  // 店舗が変わった時にキャスト一覧を取得する処理
  async function handleStoreChange() {
	if (!formData.value.store) {
	  castOptions.value = []
	  formData.value.cast = null
	  return
	}
	try {
	  const res = await api.get(`/accounts/casts/?store=${formData.value.store}`)
	  castOptions.value = res.data.casts
	} catch (e) {
	  alert('キャスト一覧の取得に失敗しました')
	}
  }
  
  // ==============================
  // 計算ロジック（フロントで実施）
  // ==============================
  function calcReservation() {
	let total = 0
  
	// 1) コースの価格を加算
	const chosenCourse = courseOptions.value.find(c => c.id === formData.value.course)
	if (chosenCourse) {
	  total += Number(chosenCourse.price) || 0
	}
  
	// 2) メニューの価格を加算
	formData.value.menus.forEach(menuId => {
	  const menuItem = menuOptions.value.find(m => m.id === menuId)
	  if (menuItem) {
		total += Number(menuItem.price) || 0
	  }
	})
  
	// 3) 予約時間 × α など（例: 1分あたり100円）
	if (formData.value.time_minutes) {
	  total += formData.value.time_minutes * 100
	}
  
	// 4) その他チェック項目
	//    - 入会金(例: 3000円) / 写真指名(500円) / 本指名(1000円) など
	//    - 割引のcheckboxがONなら0円 etc.
	if (formData.value.enrollment_fee && !formData.value.enrollment_fee_discounted) {
	  total += 3000
	}
	if (formData.value.photo_nomination_fee && !formData.value.photo_nomination_fee_discounted) {
	  total += 500
	}
	if (formData.value.regular_nomination_fee && !formData.value.regular_nomination_fee_discounted) {
	  total += 1000
	}
  
	// 5) 割引の合計額を引く
	formData.value.discounts.forEach(discountId => {
	  const discountItem = discountOptions.value.find(d => d.id === discountId)
	  if (discountItem) {
		total -= Number(discountItem.amount) || 0
	  }
	})
  
	// 6) フォームに反映
	formData.value.reservation_amount = total

  }
  
  // 更新(保存)
  async function updateReservation() {
	if (!reservationId) {
	  alert('予約IDが指定されていません')
	  return
	}
	try {
	  await api.put(`/reservations/${reservationId}/`, { ...formData.value })
	  alert('更新しました')
	  router.push('/reservations') // 一覧などへ戻る
	} catch (e) {
	  alert('更新に失敗しました')
	}
  }
  </script>
  