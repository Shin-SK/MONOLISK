	<template>
		<div class="reservation__create form">
		<h2>新規予約</h2>
	
		<!-- ===== 予約名 (customer_name) ===== -->
		<div class="box">
			<div class="head">予約名</div>
			<input type="text" v-model="formData.customer_name" placeholder="予約名" />
		</div>
	
		<!-- 店舗選択 -->
		<div class="box store">
			<div class="head">店舗</div>
				<div class="radio-group grid-default">
					<div 
					v-for="store in storeOptions" 
					:key="store.id" 
					class="radio-item"
					>
						<input
							type="radio"
							:id="'store-' + store.id"
							:value="store.id"
							v-model="selectedStoreId"
							@change="fetchStoreUsers"
						/>
						<label :for="'store-' + store.id">
							{{ store.name }}
						</label>
					</div>
				</div>
			</div>

		<!-- StoreUser選択 (キャスト + ランク情報) -->
		<div class="box" v-if="storeUserOptions.length">
				<div class="head">キャスト (StoreUser)</div>
				<div class="radio-group cast grid-default">
					<div
					v-for="su in storeUserOptions"
					:key="su.id"
					class="radio-item"
					>
						<input
							type="radio"
							:id="'storeUser-' + su.id"
							:value="su.id"
							v-model="formData.store_user"
						/>
						<label :for="'storeUser-' + su.id">
							<div class="wrap">
								<span class="nickname">{{ su.nickname }}</span>
								<span class="full">{{ su.full_name }}</span>
								<span class="rank">{{ su.rank_name }}☆{{ su.star_count }}</span>
							</div>
						</label>
					</div>
				</div><!-- cast -->
			</div><!-- box -->

			<!-- 予約開始時間 -->
			<div class="box calendar">
				<div class="calendar__wrap">
					<!-- 日付選択 (カレンダーピッカー) -->
					<VueDatePicker
					v-model="selectedDate"
					:enableTimePicker="false"
					:format="'yyyy-MM-dd'"
					value-type="format"
					class="picker"
					placeholder="日付を選択"
					/>

					<!-- 時刻入力 (time型入力) -->
					<input
					type="time"
					v-model="selectedTime"
					required
					/>
				</div>
				<div>{{ formData.start_time }}</div>


			</div>

			<!-- 予約時間(分) -->
			<div class="box">
				<div class="head">予約時間(分)</div>
				<input type="number" v-model.number="formData.time_minutes" />
			</div>

			<!-- メニュー一覧 (チェックボックス) -->
			<div class="box">
				<div class="head">メニュー</div>
				<div class="check-group grid-default">
					<div v-for="menu in menuOptions" :key="menu.id" class="check-item">
					<input
						type="checkbox"
						:id="'menu-' + menu.id"
						:value="menu.id"
						v-model="formData.menus"
					/>
					<label :for="'menu-' + menu.id">
						<span class="name">{{ menu.name }}</span>
						<span class="price">{{ menu.price }}円</span>
					</label>
					</div>
				</div>
			</div>

			<div class="box adress">
				<div class="head">住所</div>
				<div class="wrap">
					<input class="zip" type="text" v-model="formData.postal_code" placeholder="郵便番号から住所入力"></input>
					<input class="main" type="text" v-model="formData.address"></input>
				</div>
				<div class="wrap google-map">
					<div v-if="mapUrl">
						<iframe
							width="100%"
							height="300"
							style="border:0;"
							:src="`https://www.google.com/maps/embed/v1/place?q=${encodeURIComponent(formData.address)}&key=AIzaSyAfTYdOTehT3vQBWLi5pIzQC-VCjbGq4Rs`"
							allowfullscreen
							loading="lazy"
							></iframe>

					</div>
				</div>
			</div>

			<!-- 追加オプション (例: 入会金や写真指名など) -->
			<div class="box">
				<div class="head">その他</div>
				<div class="check-group grid-default">
				<div class="check-item">
					<input type="checkbox" v-model="formData.enrollment_fee" id="enrollment_fee"/>
					<label for="enrollment_fee">入会金</label>
				</div>
				<div class="check-item">
					<input type="checkbox" v-model="formData.enrollment_fee_discounted" id="enrollment_fee_discounted"/>
					<label for="enrollment_fee_discounted">入会金0円</label>
				</div>
				<div class="check-item">
					<input type="checkbox" v-model="formData.photo_nomination_fee" id="photo_nomination_fee"/>
					<label for="photo_nomination_fee">写真指名</label>
				</div>
				<div class="check-item">
					<input type="checkbox" v-model="formData.photo_nomination_fee_discounted" id="photo_nomination_fee_discounted"/>
					<label for="photo_nomination_fee_discounted">写真指名0円</label>
				</div>
				<div class="check-item">
					<input type="checkbox" v-model="formData.regular_nomination_fee" id="regular_nomination_fee"/>
					<label for="regular_nomination_fee">本指名</label>
				</div>
				<div class="check-item">
					<input type="checkbox" v-model="formData.regular_nomination_fee_discounted" id="regular_nomination_fee_discounted"/>
					<label for="regular_nomination_fee_discounted">本指名割引</label>
				</div>
				</div><!-- check-group -->
			</div>

			<div class="box">
				<div class="head">ドライバー</div>
				<div class="radio-group grid-default">
					<div
					v-for="drv in driverOptions"
					:key="drv.id"
					class="radio-item"
					>
					<input
						type="radio"
						:id="'driver-' + drv.id"
						:value="drv.id"
						v-model="formData.driver"
					/>
					<label :for="'driver-' + drv.id">
						{{ drv.full_name }}
					</label>
					</div>
				</div>
			</div>

			<div class="box ">
				<button @click="calcReservation">予約金計算</button>
			</div>

			<!-- 予約金額表示 -->
			<div class="amount">
				<div class="amount__wrap">
					<div class="head">予約金額</div>
					<div class="value">{{ formData.reservation_amount }}</div>
				</div>
			</div>

			<div class="box">
				<!-- 「作成」ボタン -->
				<button @click="createReservation">予約確定</button>
			</div>

		</div>
	</template>
	
	<script setup>
	import { ref, onMounted, watch ,computed } from 'vue'
	import { useRouter } from 'vue-router'
	import api from '@/api'
	import axios from 'axios'   // ZipCloudなどに問い合わせるために使う
	import VueDatePicker from '@vuepic/vue-datepicker'
	import '@vuepic/vue-datepicker/dist/main.css';
	
	const router = useRouter()
	
	// ==================== 各種リスト ====================
	const storeOptions = ref([])       // 店舗一覧
	const storeUserOptions = ref([])   // 店舗×キャスト(StoreUser)一覧
	const driverOptions = ref([])      // ドライバー一覧
	const menuOptions = ref([])        // メニュー一覧
	const rankOptions = ref([])        // ランク一覧 (price_60, price_75等を持つ)
	
	// ==================== フォームデータ ====================
	const selectedStoreId = ref(null)  // 選択された「店舗ID」
	
	const formData = ref({
		customer_name: '',          // 予約名
		store_user: null,           // キャスト(StoreUser)
		driver: null,               // ドライバーID
		start_time: null,             // 予約開始日時
		time_minutes: 60,           // 予約時間(分)
		menus: [],                  // 選択されたメニューIDの配列
		enrollment_fee: false,      
		photo_nomination_fee: false, 
		// ...他のフラグやフィールド
		reservation_amount: 0       // 計算結果
	})

	const selectedDate = ref(null);   // カレンダーピッカーで選んだ日付 (例: 2025-03-15)
	const selectedTime = ref('');     // 時刻入力 (例: 14:30)
	
	// ==================== マウント時処理 ====================
	onMounted(async () => {
		// ランク一覧
		await fetchRanks()
		// 店舗一覧
		await fetchStores()
		// メニュー一覧
		await fetchMenus()
		// ドライバー一覧
		await fetchDrivers()
	})

	// ==================== 日付 ====================

	watch([selectedDate, selectedTime], ([newDate, newTime]) => {
  if (newDate && newTime) {
    let dateStr = ''

    // newDate が Dateオブジェクトか文字列かを判定
    if (typeof newDate === 'string') {
      // すでに "YYYY-MM-DD" のような文字列なら、そのまま使う
      dateStr = newDate
    } else if (newDate instanceof Date) {
      // Date型なら "YYYY-MM-DD" だけ取り出す
      dateStr = newDate.toISOString().slice(0, 10)
      // 例: "2025-03-05"
    } else {
      // 万が一それ以外の型なら何もしない
      dateStr = ''
    }

    // timeStr は "HH:mm" を想定 (例: "14:30")
    const timeStr = newTime

    // ISO8601 形式で "YYYY-MM-DDTHH:mm:00" を組み立てる
    const isoString = `${dateStr}T${timeStr}:00`
    // 例: "2025-03-05T14:30:00"

    formData.value.start_time = isoString
  } else {
    // どちらかが空なら start_time はクリア
    formData.value.start_time = null
  }
})


	// ==================== watchで郵便番号の変化を監視 ====================
		watch(
		() => formData.value.postal_code,
		async (newVal) => {
			// 例：郵便番号が7桁になったタイミングでAPIに問い合わせる
			if (newVal && newVal.length === 7) {
			try {
				const { data } = await axios.get(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${newVal}`)
				// 取得成功し、候補があれば
				if (data.results && data.results.length > 0) {
				const result = data.results[0] // 先頭の候補を使う
				// 住所を結合してセットする
				formData.value.address = `${result.address1}${result.address2}${result.address3}`
				}
			} catch (error) {
				console.error('住所の自動取得に失敗:', error)
			}
			}
		}
		)

	// ==================== 地図生成 ====================
	const mapUrl = computed(() => {
	if (formData.value.address) {
		// 住所がある場合はエンコードしてgoogleマップ埋め込み用URLに
		return `https://www.google.com/maps?q=${encodeURIComponent(formData.value.address)}&output=embed`
	}
	// 住所が無い場合は空文字にして表示しない
	return ''
	})


	// ==================== API取得関数 ====================
	async function fetchRanks() {
		try {
		const { data } = await api.get('/accounts/ranks/')
		rankOptions.value = data
		} catch (err) {
		console.error('ランク一覧取得失敗', err)
		}
	}
	
	async function fetchStores() {
		try {
		const { data } = await api.get('/accounts/stores/')
		storeOptions.value = data
		} catch (e) {
		console.error('店舗一覧取得失敗', e)
		}
	}
	
	async function fetchMenus() {
		try {
		const { data } = await api.get('/reservations/menus/')
		menuOptions.value = data
		} catch (e) {
		console.error('メニュー一覧取得失敗', e)
		}
	}
	
	// ★ ドライバー一覧取得
	async function fetchDrivers() {
		try {
		// 例: /accounts/users/?role=driver
		const { data } = await api.get('/accounts/users/?role=driver')
		driverOptions.value = data
		} catch (e) {
		console.error('ドライバー一覧取得失敗', e)
		}
	}
	
	// 店舗を選んだら StoreUser一覧を取得
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
	
	// ==================== 計算処理 ====================
	function calcReservation() {
		console.log("calcReservation called!")
		let total = 0
	
		// 1) メニュー加算
		formData.value.menus.forEach(menuId => {
		const item = menuOptions.value.find(m => m.id === menuId)
		if (item) total += Number(item.price) || 0
		})
	
		// 2) 入会金など
		if (formData.value.enrollment_fee) {
		total += 5000
		}
		if (formData.value.photo_nomination_fee) {
		total += 2000
		}
	
		// 3) ランク (StoreUser) 計算
		const chosenSU = storeUserOptions.value.find(su => su.id === formData.value.store_user)
		if (chosenSU) {
		const chosenRank = rankOptions.value.find(r => r.id === chosenSU.rank_id)
		if (chosenRank) {
			// 時間別料金
			const t = formData.value.time_minutes
			if (t === 60) {
			total += chosenRank.price_60
			} else if (t === 75) {
			total += chosenRank.price_75
			} else if (t === 90) {
			total += chosenRank.price_90
			} else if (t === 120) {
			total += chosenRank.price_120
			} else if (t === 150) {
			total += chosenRank.price_150
			} else if (t === 180) {
			total += chosenRank.price_180
			}
			// 星数 × plus_per_star
			const starCount = chosenSU.star_count || 0
			total += starCount * chosenRank.plus_per_star
		}
		}
	
		formData.value.reservation_amount = total
		console.log("計算結果:", total)
	}
	
	// ==================== 予約作成(POST) ====================
	async function createReservation() {
		try {
			const payload = { ...formData.value }
			console.log('送信payload:', JSON.stringify(payload))
			const res = await api.post('/reservations/', payload)
			alert('予約を作成しました')
			router.push('/dashboard/reservations')
		} catch (e) {
			console.error('予約作成失敗', e)
			// ↓ ここでエラー情報を詳しく出力
			if (e.response) {
			console.log('=== バリデーションエラー内容 ===')
			console.log(JSON.stringify(e.response.data, null, 2))
			}
		}
	}

	</script>
	