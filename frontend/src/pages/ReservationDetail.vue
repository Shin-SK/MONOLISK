<template>
	<div class="reservation-edit">
	  <h2>予約詳細</h2>
	  <!-- IDがなければエラー表示 -->
	  <div v-if="!reservationId">
		<p>予約IDが指定されていないため編集できません。</p>
		<button @click="goBack">戻る</button>
	  </div>
  
	  <div v-else>
		<!-- ===== 店舗 (Store) ===== -->
		<div class="section">
		  <label>店舗：</label>
		  <select v-model="formData.store" @change="handleStoreChange">
			<option value="">店舗を選択</option>
			<option
			  v-for="storeOption in storeOptions"
			  :key="storeOption.id"
			  :value="storeOption.id"
			>
			  {{ storeOption.name }}
			</option>
		  </select>
		</div>
  
		<!-- ===== キャスト (Cast) ===== -->
		<div class="section">
		  <label>キャスト：</label>
		  <select v-model="formData.cast">
			<option value="">キャストを選択</option>
			<option
			  v-for="castOption in castOptions"
			  :key="castOption.id"
			  :value="castOption.id"
			>
			  {{ castOption.full_name }}
			</option>
		  </select>
		</div>
  
		<!-- ===== ドライバー (Driver) ===== -->
		<div class="section">
		  <label>ドライバー：</label>
		  <select v-model="formData.driver">
			<option value="">ドライバーを選択</option>
			<option
			  v-for="driverOption in driverOptions"
			  :key="driverOption.id"
			  :value="driverOption.id"
			>
			  {{ driverOption.full_name }}
			</option>
		  </select>
		</div>
  
		<!-- ===== 顧客名 (customer_name) ===== -->
		<div class="section">
		  <label>お客様の名前：</label>
		  <input v-model="formData.customer_name" type="text" />
		</div>
  
		<!-- ===== 開始時間 (start_time) ===== -->
		<div class="section">
		  <label>開始時間：</label>
		  <input v-model="formData.start_time" type="datetime-local" />
		</div>
  
		<!-- ===== コース (course) ===== -->
		<div class="section">
		  <label>コース：</label>
		  <select v-model="formData.course">
			<option value="">コースを選択</option>
			<option
			  v-for="courseOption in courseOptions"
			  :key="courseOption.id"
			  :value="courseOption.id"
			>
			  {{ courseOption.name }}
			</option>
		  </select>
		</div>
  
		<!-- ===== メニュー (menus) 多対多 ===== -->
		<div class="section">
		  <label>メニュー：</label>
		  <div v-for="menuOption in menuOptions" :key="menuOption.id">
			<input
			  type="checkbox"
			  :value="menuOption.id"
			  v-model="formData.menus"
			/>
			{{ menuOption.name }}
		  </div>
		</div>
  
		<!-- ===== 会員種別 (membership_type) ===== -->
		<div class="section">
		  <label>会員種別：</label>
		  <!-- 選択肢例: new, general, member -->
		  <select v-model="formData.membership_type">
			<option value="new">新規</option>
			<option value="general">一般会員</option>
			<option value="member">本会員</option>
		  </select>
		</div>
  
		<!-- ===== 予約時間 (time_minutes) ===== -->
		<div class="section">
		  <label>予約時間（分）：</label>
		  <input v-model.number="formData.time_minutes" type="number" />
		</div>
  
		<!-- ===== 予約金額 (reservation_amount) 読み取り専用 ===== -->
		<div class="section">
		  <label>予約金額：</label>
		  <input :value="formData.reservation_amount" disabled />
		</div>
  
		<!-- ===== 割引 (discounts) 多対多 ===== -->
		<div class="section">
		  <label>割引：</label>
		  <div v-for="discountOption in discountOptions" :key="discountOption.id">
			<input
			  type="checkbox"
			  :value="discountOption.id"
			  v-model="formData.discounts"
			/>
			{{ discountOption.name }}
		  </div>
		</div>
  
		<!-- ===== 入会金 (enrollment_fee) ===== -->
		<div class="section">
		  <label>入会金：</label>
		  <input type="checkbox" v-model="formData.enrollment_fee" />
		  <span>有無</span>
		  <input type="checkbox" v-model="formData.enrollment_fee_discounted" />
		  <span>入会金0円（期間限定）</span>
		</div>
  
		<!-- ===== 写真指名 (photo_nomination_fee) ===== -->
		<div class="section">
		  <label>写真指名：</label>
		  <input type="checkbox" v-model="formData.photo_nomination_fee" />
		  <span>有無</span>
		  <input
			type="checkbox"
			v-model="formData.photo_nomination_fee_discounted"
		  />
		  <span>写真指名0円（期間限定）</span>
		</div>
  
		<!-- ===== 本指名 (regular_nomination_fee) ===== -->
		<div class="section">
		  <label>本指名：</label>
		  <input type="checkbox" v-model="formData.regular_nomination_fee" />
		  <span>有無</span>
		  <input
			type="checkbox"
			v-model="formData.regular_nomination_fee_discounted"
		  />
		  <span>本指名割引</span>
		</div>
  
		<!-- ===== キャスト受取金 (cast_received) ===== -->
		<div class="section">
		  <label>キャスト受取金：</label>
		  <input v-model.number="formData.cast_received" type="number" />
		</div>
  
		<!-- ===== ドライバー受取金 (driver_received) ===== -->
		<div class="section">
		  <label>ドライバー受取金：</label>
		  <input v-model.number="formData.driver_received" type="number" />
		</div>
  
		<!-- ===== 店舗受取金 (store_received) ===== -->
		<div class="section">
		  <label>店舗受取金：</label>
		  <input v-model.number="formData.store_received" type="number" />
		</div>
  
		<!-- 更新ボタン -->
		<button @click="updateReservation">
		  更新
		</button>
	  </div>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import api from '@/api'
  
  const router = useRouter()
  const route = useRoute()
  
  // URL から予約IDを取得（必須）
  const reservationId = route.params.id || null
  
  // ==== 選択肢一覧 (Store, Cast, Driver, Course, Menu, Discount) ====
  // ここでは単純に全取得している例
  const storeOptions = ref([])
  const castOptions = ref([])
  const driverOptions = ref([])
  const courseOptions = ref([])
  const menuOptions = ref([])
  const discountOptions = ref([])
  
  // ==== フォームデータ ====
  const formData = ref({
	customer_name: '',
	start_time: '',
	store: null,
	cast: null,
	driver: null,
	course: null,
	menus: [],           // 多対多: 初期値は空配列
	membership_type: 'general',
	time_minutes: null,
	reservation_amount: 0, // read-only想定
	discounts: [],       // 多対多: 初期値は空配列
	enrollment_fee: false,
	enrollment_fee_discounted: false,
	photo_nomination_fee: false,
	photo_nomination_fee_discounted: false,
	regular_nomination_fee: false,
	regular_nomination_fee_discounted: false,
	cast_received: null,
	driver_received: null,
	store_received: null,
  })
  
  // 画面マウント時に一覧取得＆予約取得
  onMounted(async () => {
	await fetchInitialData()
	if (reservationId) {
	  await fetchReservation(reservationId)
	}
  })
  
  // 最初に選択肢データを取得
  const fetchInitialData = async () => {
	try {
	  // 店舗一覧
	  let res = await api.get('/accounts/stores/')
	  storeOptions.value = res.data  // [{id, name}, ...]
  
	  // キャスト一覧 (role="cast" のUser一覧), 実装次第で /accounts/casts/ ?store=~ など
	  // ここでは一旦 cast 一覧を全取得と仮定
	  let allCasts = await api.get('/accounts/users/?role=cast')
	  castOptions.value = allCasts.data // 例: [{id, full_name}, ...]
  
	  // ドライバー一覧 (role="driver")
	  let allDrivers = await api.get('/accounts/users/?role=driver')
	  driverOptions.value = allDrivers.data
  
	  // コース一覧
	  let courses = await api.get('/reservations/courses/')
	  courseOptions.value = courses.data // 例: [{id, name, price}, ...]
  
	  // メニュー一覧
	  let menus = await api.get('/reservations/menus/')
	  menuOptions.value = menus.data // 例: [{id, name, price}, ...]
  
	  // 割引一覧
	  let discounts = await api.get('/reservations/discounts/')
	  discountOptions.value = discounts.data // 例: [{id, name, amount}, ...]
	} catch (err) {
	  console.error('初期データ取得失敗:', err)
	}
  }
  
  // 予約データをGETしてformDataに反映
  const fetchReservation = async (id) => {
	try {
	  const { data } = await api.get(`/reservations/${id}/`)
	  // バックエンドのレスポンスから formData に割り当てる
	  formData.value.customer_name = data.customer_name
	  formData.value.start_time = data.start_time || ''
	  formData.value.store = data.store ? data.store.id : null
	  formData.value.cast = data.cast ? data.cast.id : null
	  formData.value.driver = data.driver ? data.driver.id : null
	  formData.value.course = data.course ? data.course.id : null
	  formData.value.menus = data.menus ? data.menus.map(m => m.id) : []
	  formData.value.membership_type = data.membership_type || 'general'
	  formData.value.time_minutes = data.time_minutes
	  formData.value.reservation_amount = data.reservation_amount
	  formData.value.discounts = data.discounts 
		? data.discounts.map(d => typeof d === 'object' ? d.id : d)
		: []
	  formData.value.enrollment_fee = data.enrollment_fee
	  formData.value.enrollment_fee_discounted = data.enrollment_fee_discounted
	  formData.value.photo_nomination_fee = data.photo_nomination_fee
	  formData.value.photo_nomination_fee_discounted = data.photo_nomination_fee_discounted
	  formData.value.regular_nomination_fee = data.regular_nomination_fee
	  formData.value.regular_nomination_fee_discounted = data.regular_nomination_fee_discounted
	  formData.value.cast_received = data.cast_received
	  formData.value.driver_received = data.driver_received
	  formData.value.store_received = data.store_received
	} catch (error) {
	  console.error('予約詳細取得失敗:', error)
	}
  }
  
  // 予約の更新
  const updateReservation = async () => {
	if (!reservationId) {
	  alert("予約IDが存在しません。")
	  return
	}
	try {
	  // PUT用のpayload
	  const payload = { ...formData.value }
	  console.log('送信payload:', payload)
  
	  const res = await api.put(`/reservations/${reservationId}/`, payload)
	  console.log('予約更新成功:', res.data)
  
	  // 更新後の動き：再取得 or 一覧に戻る etc.
	  await fetchReservation(res.data.id) 
	  alert("更新しました")
	} catch (error) {
	  console.error('予約更新失敗:', error)
	}
  }
  
  // 店舗が変わったら、キャスト選択をリセット or 再取得したい場合はここで処理
  const handleStoreChange = () => {
	// もし店舗ごとにキャスト一覧が違うなら
	// fetchCasts(formData.value.store) などして再取得する等
	// ここでは省略
  }
  
  // 戻る
  const goBack = () => {
	router.push('/reservations') // 一覧ページへ戻る例
  }
  </script>
  
  <style scoped>
  .reservation-edit {
	/* お好みで */
  }
  .section {
	margin-bottom: 1em;
  }
  </style>
  