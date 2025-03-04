<template>
	<div class="reservation__edit">
	  <h2>予約編集</h2>
	  <!-- IDがなければエラー表示 -->
	  <div v-if="!reservationId">
		<p>予約IDが指定されていないため編集できません。</p>
		<button @click="goBack">戻る</button>
	  </div>
  
	  <div v-else>

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
		<!-- <div class="area radio cast">
			<div class="head">キャスト</div>
			<div class="value">
				<div class="value__inner" v-for="castOption in castOptions" :key="castOption.id">
					<input 
						type="radio" 
						v-model="formData.cast" 
						:id="'radio-cast-' + castOption.user_id"
						:value="castOption.user_id"
						class="value__inner--input"
					/>
					<label :for="'radio-cast-' + castOption.user_id" class="value__inner--label">
						{{ castOption.nickname }}
					</label>
				</div>
			</div>
		</div> -->

		<!-- ===== キャスト (Cast) ===== -->
		<div class="area radio cast">
		<div class="head">キャスト</div>
		<div class="value">
			<div class="value__inner" v-for="castOption in castOptions" :key="castOption.id">
				<!-- 1人分のキャストに対するラジオ入力 -->
				<input 
					type="radio" 
					v-model="formData.cast" 
					:id="'radio-cast-' + castOption.id"
					:value="castOption.id"
					class="value__inner--input"
				/>
				<!-- 複数の店舗に対して個別のラベルを生成 -->
				<label 
					v-for="(store, index) in castOption.stores" 
					:key="index" 
					:for="'radio-cast-' + castOption.id" 
					class="value__inner--label"
				>
					{{ store.nickname }}
				</label>
				<!-- もし店舗情報がない場合は username を表示 -->
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


		<!-- ===== その他 (enrollment_fee) ===== -->
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

		<!-- ========== 予約金額 (reservation_amount) 読み取り専用 ========== -->
		<div class="area--reservation_amount">
			<div class="box">
				<div class="head">予約金額</div>
				<div class="cell">
					{{ formData.reservation_amount }}
				</div>
			</div>
		</div>


		<div class="area--input">
			<!-- ===== キャスト受取金 (cast_received) ===== -->
			<div class="wrap">
				<div class="box">
				<label>キャスト受取金</label>
				<input v-model.number="formData.cast_received" type="number" />
				</div>
		
				<!-- ===== ドライバー受取金 (driver_received) ===== -->
				<div class="box">
				<label>ドライバー受取金</label>
				<input v-model.number="formData.driver_received" type="number" />
				</div>
		
				<!-- ===== 店舗受取金 (store_received) ===== -->
				<div class="box">
				<label>店舗受取金</label>
				<input v-model.number="formData.store_received" type="number" />
				</div>
			</div>
		</div>
		<!-- 更新ボタン -->
		<button class="submit" @click="updateReservation">更新</button>
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
  
  // ==== 選択肢一覧 (Store, Driver, Course, Menu, Discount) ====
  // ※ キャストは「店舗ごとに取得」するので、全キャストは取得しない
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
  
  // 画面マウント時に各種データ取得 & 予約詳細の読込
  onMounted(async () => {
	await fetchInitialData()
  
	if (reservationId) {
	  await fetchReservation(reservationId)
	}
  })
  
  // 初期データ（店舗一覧・ドライバー一覧・コース一覧など）
  const fetchInitialData = async () => {
	try {
	  // 店舗一覧
	  let storeRes = await api.get('/accounts/stores/')
	  storeOptions.value = storeRes.data // [{id, name}, ...]
  
	  // ドライバー一覧
	  let driverRes = await api.get('/accounts/users/?role=driver')
	  driverOptions.value = driverRes.data
  
	  // コース一覧
	  let courses = await api.get('/reservations/courses/')  // バックエンドルートに合わせる
	  courseOptions.value = courses.data
  
	  // メニュー一覧
	  let menus = await api.get('/reservations/menus/')
	  menuOptions.value = menus.data
  
	  // 割引一覧
	  let discounts = await api.get('/reservations/discounts/')
	  discountOptions.value = discounts.data
	} catch (err) {
	  console.error('初期データ取得失敗:', err)
	}
  }
  
  // 予約データをGETしてformDataに反映
  const fetchReservation = async (id) => {
	try {
	  const { data } = await api.get(`/reservations/${id}/`)
	  formData.value.customer_name = data.customer_name
	  formData.value.start_time = data.start_time || ''
	  // 店舗
	  if (data.store) {
		formData.value.store = data.store.id
		// 店舗をセットしたらキャスト一覧を取得
		await handleStoreChange()
	  }
	  // キャスト
	  // いま取得した一覧の中に、data.cast.idがあればセット
	  if (data.cast) {
		formData.value.cast = data.cast.id
	  }

	  // ドライバー
	  formData.value.driver = data.driver ? data.driver.id : null
	  // コース
	  formData.value.course = data.course ? data.course.id : null
	  // メニュー
	  formData.value.menus = data.menus ? data.menus.map(m => m.id) : []
	  formData.value.membership_type = data.membership_type || 'general'
	  formData.value.time_minutes = data.time_minutes
	  formData.value.reservation_amount = data.reservation_amount
	  // 割引
	  formData.value.discounts = data.discounts 
		? data.discounts.map(d => (typeof d === 'object') ? d.id : d)
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
  
  // 店舗が変わったとき→その店舗に紐づくキャストを取得
  const handleStoreChange = async () => {
	const storeId = formData.value.store
	if (!storeId) {
	  castOptions.value = []
	  formData.value.cast = null
	  return
	}
	try {
	  // /accounts/casts/?store=◯◯ のエンドポイントで取得
	  const res = await api.get(`/accounts/casts/?store=${storeId}`)
	  // 例: { casts: [ { user_id: 10, full_name: "...", nickname: "..."}, ... ] }
	  castOptions.value = res.data.casts
	  // もし既に選んでいたキャストが新しい一覧にいなければ、castをnullにするなど
	} catch (error) {
	  console.error('店舗に紐づくキャスト取得失敗:', error)
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
  
	  // 更新後に再取得 or 一覧へ戻るなど
	  await fetchReservation(res.data.id) 
	  alert("更新しました")
	} catch (error) {
	  console.error('予約更新失敗:', error)
	}
  }
  
  // 戻る
  const goBack = () => {
	router.push('/reservations') // 一覧ページへ戻る
  }
  </script>
  