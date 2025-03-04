<template>
	<div class="reservation__create">
	  <h2>予約作成</h2>
  
	  <!-- ===== 店舗 (Store) ===== -->
	  <div class="area radio store">
		<div class="head">店舗</div>
		<div class="value">
		  <div class="value__inner" v-for="storeOption in storeOptions" :key="storeOption.id">
			<input 
			  type="radio" 
			  v-model="formData.store" 
			  :id="'radio-store-' + storeOption.id"
			  :value="storeOption.id"
			  @change="handleStoreChange"
			/>
			<label :for="'radio-store-' + storeOption.id">{{ storeOption.name }}</label>
		  </div>
		</div>
	  </div>
  
	  <!-- ===== キャスト (Cast) ===== -->
	  <div class="area radio cast">
		<div class="head">キャスト</div>
		<div class="value">
		  <div class="value__inner" v-for="castOption in castOptions" :key="castOption.id">
			<input 
			  type="radio" 
			  v-model="formData.cast" 
			  :id="'radio-cast-' + castOption.id"
			  :value="castOption.id"
			/>
			<label
			  v-for="(store, index) in castOption.stores" 
			  :key="index"
			  :for="'radio-cast-' + castOption.id"
			>
			  {{ store.nickname }}
			</label>
			<!-- 店舗情報がない場合 -->
			<label 
			  v-if="!castOption.stores || castOption.stores.length === 0" 
			  :for="'radio-cast-' + castOption.id"
			>
			  {{ castOption.nickname }}
			</label>
		  </div>
		</div>
	  </div>
  
	  <!-- ===== ドライバー (Driver) ===== -->
	  <div class="area radio">
		<div class="head">ドライバー</div>
		<div class="value">
		  <div class="value__inner" v-for="driverOption in driverOptions" :key="driverOption.id">
			<input 
			  type="radio" 
			  v-model="formData.driver" 
			  :id="'radio-driver-' + driverOption.id"
			  :value="driverOption.id"
			/>
			<label :for="'radio-driver-' + driverOption.id">{{ driverOption.full_name }}</label>
		  </div>
		</div>
	  </div>
  
	  <!-- ===== 顧客名 (customer_name) ===== -->
	  <div class="area text">
		<div class="head">ご予約名</div>
		<input v-model="formData.customer_name" type="text" />
	  </div>
  
	  <!-- ===== 開始時間 (start_time) ===== -->
	  <div class="area calendar">
		<div class="head">ご予約日時</div>
		<input v-model="formData.start_time" type="datetime-local" />
	  </div>
  
	  <!-- ===== コース (course) ===== -->
	  <div class="area radio course">
		<div class="head">コース</div>
		<div class="value">
		  <div class="value__inner" v-for="courseOption in courseOptions" :key="courseOption.id">
			<input 
			  type="radio" 
			  v-model="formData.course" 
			  :id="'radio-course-' + courseOption.id"
			  :value="courseOption.id"
			/>
			<label :for="'radio-course-' + courseOption.id">
			  {{ courseOption.name }} ({{ courseOption.price }}円)
			</label>
		  </div>
		</div>
	  </div>
  
	  <!-- ===== メニュー (menus) ===== -->
	  <div class="area checkbox menu">
		<div class="head">メニュー</div>
		<div class="value">
		  <div class="value__inner" v-for="menuOption in menuOptions" :key="menuOption.id">
			<input 
			  type="checkbox" 
			  v-model="formData.menus" 
			  :id="'checkbox-menu-' + menuOption.id"
			  :value="menuOption.id"
			/>
			<label :for="'checkbox-menu-' + menuOption.id">
			  {{ menuOption.name }} ({{ menuOption.price }}円)
			</label>
		  </div>
		</div>
	  </div>
  
	  <!-- ===== 会員種別 (membership_type) ===== -->
	  <div class="area radio membership">
		<div class="head">会員種別</div>
		<div class="value">
		  <label>
			<input 
			  type="radio" 
			  v-model="formData.membership_type" 
			  value="new"
			/>
			新規
		  </label>
		  <label>
			<input 
			  type="radio" 
			  v-model="formData.membership_type" 
			  value="general"
			/>
			一般会員
		  </label>
		  <label>
			<input 
			  type="radio" 
			  v-model="formData.membership_type" 
			  value="member"
			/>
			本会員
		  </label>
		</div>
	  </div>
  
	  <!-- ===== 予約時間 (time_minutes) ===== -->
	  <div class="area number">
		<div class="head">予約時間(分)</div>
		<input v-model.number="formData.time_minutes" type="number" />
	  </div>
  
	  <!-- ===== 割引 (discounts) ===== -->
	  <div class="area checkbox discount">
		<div class="head">割引</div>
		<div class="value">
		  <div class="value__inner" v-for="discountOption in discountOptions" :key="discountOption.id">
			<input
			  type="checkbox"
			  v-model="formData.discounts"
			  :value="discountOption.id"
			  :id="'checkbox-discount-' + discountOption.id"
			/>
			<label :for="'checkbox-discount-' + discountOption.id">
			  {{ discountOption.name }} ({{ discountOption.amount }}円引き)
			</label>
		  </div>
		</div>
	  </div>
  
	  <!-- ===== その他 (enrollment_fee, etc.) ===== -->
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
  
	  <!-- ===== 予約金額 (reservation_amount) ===== -->
	  <div class="area--reservation_amount">
		<div class="head">予約金額</div>
		<div>{{ formData.reservation_amount }}</div>
	  </div>
  
	  <!-- ===== キャスト・ドライバー・店舗受取金 ===== -->
	  <div class="area--input">
		<div>
		  <label>キャスト受取金</label>
		  <input v-model.number="formData.cast_received" type="number" />
		</div>
		<div>
		  <label>ドライバー受取金</label>
		  <input v-model.number="formData.driver_received" type="number" />
		</div>
		<div>
		  <label>店舗受取金</label>
		  <input v-model.number="formData.store_received" type="number" />
		</div>
	  </div>
  
	  <!-- ===== 計算ボタン & 作成ボタン ===== -->
	  <button @click="calcReservation">計算</button>
	  <button class="submit" @click="createReservation">作成</button>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import api from '@/api'
  
  const router = useRouter()
  
  // 選択肢一覧 (Store, Driver, Course, Menu, Discount)
  const storeOptions = ref([])
  const castOptions = ref([])
  const driverOptions = ref([])
  const courseOptions = ref([])
  const menuOptions = ref([])
  const discountOptions = ref([])
  
  // フォームデータ
  const formData = ref({
	customer_name: '',
	start_time: '',
	store: null,
	cast: null,
	driver: null,
	course: null,
	menus: [],
	membership_type: 'general',
	time_minutes: 0,
	reservation_amount: 0,
	discounts: [],
	enrollment_fee: false,
	enrollment_fee_discounted: false,
	photo_nomination_fee: false,
	photo_nomination_fee_discounted: false,
	regular_nomination_fee: false,
	regular_nomination_fee_discounted: false,
	cast_received: 0,
	driver_received: 0,
	store_received: 0,
  })
  
  // 初期データ取得
  onMounted(async () => {
	await fetchInitialData()
	// 全キャスト取得したいなら、下記のような実装でもOK
	// const res = await api.get('/accounts/users/')
	// castOptions.value = res.data.filter(user => user.role === 'cast')
  })
  
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
	  console.error('初期データ取得失敗:', e)
	}
  }
  
  // 店舗が変わったら、該当のキャストリストを取得
  async function handleStoreChange() {
	if (!formData.value.store) {
	  castOptions.value = []
	  formData.value.cast = null
	  return
	}
	try {
	  const res = await api.get(`/accounts/casts/?store=${formData.value.store}`)
	  castOptions.value = res.data.casts
	} catch (error) {
	  console.error('店舗に紐づくキャスト取得失敗:', error)
	}
  }
  
  // ====== 計算ロジック (フロントで実施) ======
  function calcReservation() {
	let total = 0
  
	// コースの価格
	const chosenCourse = courseOptions.value.find(c => c.id === formData.value.course)
	if (chosenCourse) {
	  total += Number(chosenCourse.price) || 0
	}
  
	// メニューの価格合計
	formData.value.menus.forEach(menuId => {
	  const menuItem = menuOptions.value.find(m => m.id === menuId)
	  if (menuItem) {
		total += Number(menuItem.price) || 0
	  }
	})
  
	// 予約時間 × α (例: 1分100円)
	if (formData.value.time_minutes) {
	  total += formData.value.time_minutes * 100
	}
  
	// 入会金などチェック
	// - 入会金 (例: 3000円)
	if (formData.value.enrollment_fee && !formData.value.enrollment_fee_discounted) {
	  total += 3000
	}
	// 写真指名(500円)
	if (formData.value.photo_nomination_fee && !formData.value.photo_nomination_fee_discounted) {
	  total += 500
	}
	// 本指名(1000円)
	if (formData.value.regular_nomination_fee && !formData.value.regular_nomination_fee_discounted) {
	  total += 1000
	}
  
	// 割引の合計額を減算
	formData.value.discounts.forEach(discountId => {
	  const discountItem = discountOptions.value.find(d => d.id === discountId)
	  if (discountItem) {
		total -= Number(discountItem.amount) || 0
	  }
	})
  
	// 計算結果をフォームに反映
	formData.value.reservation_amount = total
  
	// ※キャスト/ドライバー/店舗受取金を自動計算したいならここで分配してもOK
	// 今回はサンプルとして省略
  }
  
  // ====== 作成(POST) ======
  async function createReservation() {
	try {
	  // 必要ならcalcReservation() を自動的に呼ぶ
	  // calcReservation()
  
	  const payload = { ...formData.value }
	  // 新規POST
	  const res = await api.post('/reservations/', payload)
	  alert('予約を作成しました')
	  // 作成したIDにリダイレクト
	  router.push(`/dashboard/reservations/${res.data.id}`)
	} catch (error) {
	  console.error('予約作成失敗:', error)
	  alert('作成に失敗しました')
	}
  }
  </script>
  