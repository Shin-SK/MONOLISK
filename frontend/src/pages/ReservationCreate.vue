<template>
	<div class="reservation__create">
	  <h2>予約作成</h2>
	  <!-- フォームは編集時とほぼ同じ。既存データはないので全項目は空状態または初期値 -->
	  
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
			  class="value__inner--input"
			/>
			<label :for="'radio-store-' + storeOption.id" class="value__inner--label">
			  {{ storeOption.name }}
			</label>
		  </div>
		</div>
	  </div>
	
	<!-- ===== キャスト (Cast) ===== -->
	<div class="area radio cast">
		<div class="head">キャスト</div>
		<div class="value">
			<div class="value__inner" v-for="castOption in castOptions" :key="castOption.id">
				<div class="d-contents">
					<input 
						type="radio" 
						v-model="formData.cast" 
						:id="'radio-cast-' + castOption.id"
						:value="castOption.id"
						class="value__inner--input"
					/>
					<label 
					v-for="(store, index) in castOption.stores" 
					:key="index" 
					:for="'radio-cast-' + castOption.id" 
					class="value__inner--label"
					>
					{{ store.nickname }}
					</label>
					<label 
					v-if="!castOption.stores || castOption.stores.length === 0" 
					:for="'radio-cast-' + castOption.id" 
					class="value__inner--label"
					>
					{{ castOption.nickname }}
					</label>
				</div>
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
			  class="value__inner--input"
			/>
			<label :for="'radio-driver-' + driverOption.id" class="value__inner--label">
			  {{ driverOption.full_name }}
			</label>
		  </div>
		</div>
	  </div>
	
	  <!-- ===== 顧客名 (customer_name) ===== -->
	  <div class="area text">
		<div class="haed">ご予約名</div>
		<div class="box">
		  <div class="current-value">{{ formData.customer_name }}</div>
		  <input v-model="formData.customer_name" type="text" />
		</div>
	  </div>
	
	  <!-- ===== 開始時間 (start_time) ===== -->
	  <div class="area calendar">
		<div class="haed">ご予約日時</div>
		<div class="box">
		  <div class="current-value">{{ formData.start_time }}</div>
		  <input v-model="formData.start_time" type="datetime-local" />
		</div>
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
			  class="value__inner--input"
			/>
			<label :for="'radio-course-' + courseOption.id" class="value__inner--label">
			  {{ courseOption.name }}
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
			  class="value__inner--input"
			/>
			<label :for="'checkbox-menu-' + menuOption.id" class="value__inner--label">
			  {{ menuOption.name }}
			</label>
		  </div>
		</div>
	  </div>
	
	  <!-- ===== 会員種別 (membership_type) ===== -->
	  <div class="area radio membership">
		<div class="head">会員種別</div>
		<div class="value">
		  <div class="value__inner">
			<input 
			  type="radio" 
			  v-model="formData.membership_type" 
			  id="radio-membership-new" 
			  value="new"
			  class="value__inner--input" />
			<label for="radio-membership-new" class="value__inner--label">新規</label>
		  </div>
		  <div class="value__inner">
			<input 
			  type="radio" 
			  v-model="formData.membership_type" 
			  id="radio-membership-general" 
			  value="general"
			  class="value__inner--input" />
			<label for="radio-membership-general" class="value__inner--label">一般会員</label>
		  </div>
		  <div class="value__inner">
			<input 
			  type="radio" 
			  v-model="formData.membership_type" 
			  id="radio-membership-member" 
			  value="member"
			  class="value__inner--input" />
			<label for="radio-membership-member" class="value__inner--label">本会員</label>
		  </div>
		</div>
	  </div>
	
	  <!-- ===== 予約時間 (time_minutes) ===== -->
	  <div class="area number">
		<div class="head">予約時間</div>
		<div class="box">
		  <div class="current-value">{{ formData.time_minutes }}</div>
		  <input v-model.number="formData.time_minutes" type="number" class="value__inner--input" />
		</div>
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
			  class="value__inner--input"
			/>
			<label :for="'checkbox-discount-' + discountOption.id" class="value__inner--label">
			  {{ discountOption.name }}
			</label>
		  </div>
		</div>
	  </div>
	
	  <!-- ===== その他 (enrollment_fee, etc.) ===== -->
	  <div class="area checkbox">
		<div class="head">その他</div>
		<div class="value">
		  <div class="value__inner">
			<input type="checkbox" v-model="formData.enrollment_fee" id="enrollment_fee" class="value__inner--input"/>
			<label for="enrollment_fee" class="value__inner--label">入会金あり</label>
		  </div>
		  <div class="value__inner">
			<input type="checkbox" v-model="formData.enrollment_fee_discounted" class="value__inner--input" id="enrollment_fee_discounted"/>
			<label for="enrollment_fee_discounted" class="value__inner--label">入会金0円（期間限定）</label>
		  </div>
		  <div class="value__inner">
			<input type="checkbox" v-model="formData.photo_nomination_fee" class="value__inner--input" id="photo_nomination_fee"/>
			<label for="photo_nomination_fee" class="value__inner--label">写真指名あり</label>
		  </div>
		  <div class="value__inner">
			<input type="checkbox" v-model="formData.photo_nomination_fee_discounted" class="value__inner--input" id="photo_nomination_fee_discounted"/>
			<label for="photo_nomination_fee_discounted" class="value__inner--label">写真指名0円（期間限定）</label>
		  </div>
		  <div class="value__inner">
			<input type="checkbox" v-model="formData.regular_nomination_fee" class="value__inner--input" id="regular_nomination_fee"/>
			<label for="regular_nomination_fee" class="value__inner--label">本指名あり</label>
		  </div>
		  <div class="value__inner">
			<input type="checkbox" v-model="formData.regular_nomination_fee_discounted" class="value__inner--input" id="regular_nomination_fee_discounted"/>
			<label for="regular_nomination_fee_discounted" class="value__inner--label">本指名割引</label>
		  </div>
		</div>
	  </div>
	
	  <!-- ===== 予約金額 (reservation_amount) 読み取り専用 ===== -->
	  <div class="area--reservation_amount">
		<div class="box">
		  <div class="head">予約金額</div>
		  <div class="cell">
			{{ formData.reservation_amount }}
		  </div>
		</div>
	  </div>
	
	  <!-- ===== キャスト・ドライバー・店舗受取金 ===== -->
	  <div class="area--input">
		<div class="wrap">
		  <div class="box">
			<label>キャスト受取金</label>
			<input v-model.number="formData.cast_received" type="number" />
		  </div>
		  <div class="box">
			<label>ドライバー受取金</label>
			<input v-model.number="formData.driver_received" type="number" />
		  </div>
		  <div class="box">
			<label>店舗受取金</label>
			<input v-model.number="formData.store_received" type="number" />
		  </div>
		</div>
	  </div>
	
	  <!-- 作成ボタン -->
	  <button class="submit" @click="createReservation">作成</button>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import api from '@/api'
  
  const router = useRouter()
  // create ページでは予約IDは存在しない
  const reservationId = null
  
  // ==== 選択肢一覧 (Store, Driver, Course, Menu, Discount) ====
  const storeOptions = ref([])
  const castOptions = ref([])
  const driverOptions = ref([])
  const courseOptions = ref([])
  const menuOptions = ref([])
  const discountOptions = ref([])
  
  // ==== フォームデータ（新規作成なので初期値） ====
  const formData = ref({
	customer_name: '',
	start_time: '',
	store: null,
	cast: null,
	driver: null,
	course: null,
	menus: [],
	membership_type: 'general',
	time_minutes: null,
	reservation_amount: 0,
	discounts: [],
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
  
  onMounted(async () => {
	await fetchInitialData();
	const res = await api.get('/accounts/users/');
	castOptions.value = res.data.filter(user => user.role === 'cast');
  });

  
  const fetchInitialData = async () => {
	try {
	  let storeRes = await api.get('/accounts/stores/')
	  storeOptions.value = storeRes.data
	  let driverRes = await api.get('/accounts/users/?role=driver')
	  driverOptions.value = driverRes.data
	  let courses = await api.get('/reservations/courses/')
	  courseOptions.value = courses.data
	  let menus = await api.get('/reservations/menus/')
	  menuOptions.value = menus.data
	  let discounts = await api.get('/reservations/discounts/')
	  discountOptions.value = discounts.data
	} catch (err) {
	  console.error('初期データ取得失敗:', err)
	}
  }
  
  const handleStoreChange = async () => {
	const storeId = formData.value.store
	if (!storeId) {
	  castOptions.value = []
	  formData.value.cast = null
	  return
	}
	try {
	  const res = await api.get(`/accounts/casts/?store=${storeId}`)
	  castOptions.value = res.data.casts
	} catch (error) {
	  console.error('店舗に紐づくキャスト取得失敗:', error)
	}
  }
  
  const createReservation = async () => {
	try {
	  const payload = { ...formData.value }
	  console.log('送信payload:', payload)
	  // POST で新規予約を作成
	  const res = await api.post('/reservations/', payload)
	  console.log('予約作成成功:', res.data)
	  // 作成後、詳細ページなどに遷移させる
	  router.push(`/dashboard/reservations/${res.data.id}`)
	  alert('作成しました')
	} catch (error) {
	  console.error('予約作成失敗:', error)
	}
  }
  </script>
  