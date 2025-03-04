<template>
	<div class="reservation-form">
	  <!-- タイトルをモードに応じて切り替え -->
	  <h2 v-if="isEdit">予約編集</h2>
	  <h2 v-else>新規予約</h2>
  
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
  
	  <!-- キャスト (StoreUser) 選択 -->
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
  
	  <!-- 予約開始時間 -->
	  <div>
		<label>開始時刻</label>
		<input type="datetime-local" v-model="formData.start_time" />
	  </div>
  
	  <!-- 予約時間(分) -->
	  <div>
		<label>予約時間(分)</label>
		<input type="number" v-model.number="formData.time_minutes" />
	  </div>
  
	  <!-- メニュー (checkbox) -->
	  <div>
		<label>メニュー</label>
		<div v-for="menu in menuOptions" :key="menu.id">
		  <input
			type="checkbox"
			:value="menu.id"
			v-model="formData.menus"
		  />
		  {{ menu.name }} ({{ menu.price }}円)
		</div>
	  </div>
  
	  <!-- 追加オプション -->
	  <div class="area checkbox">
		<div class="head">その他</div>
		<div class="value">
		  <div>
			<input type="checkbox" v-model="formData.enrollment_fee" />
			入会金
		  </div>
		  <div>
			<input type="checkbox" v-model="formData.photo_nomination_fee" />
			写真指名
		  </div>
		  <!-- 必要に応じて他のオプションを追加 -->
		</div>
	  </div>
  
	  <!-- 予約金額表示 -->
	  <div>
		<label>予約金額</label>
		{{ formData.reservation_amount }}
	  </div>
  
	  <!-- 「計算」ボタン -->
	  <button @click="calcReservation">計算</button>
  
	  <!-- 「保存」ボタン：Create or Update -->
	  <button @click="saveReservation">
		{{ isEdit ? "更新" : "作成" }}
	  </button>
	</div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import api from '@/api' // axiosインスタンス
  
  // ============ ルータ関連 ============
  // URL上の :id があれば編集モード、なければ新規作成
  const route = useRoute()
  const router = useRouter()
  const reservationId = route.params.id || null
  // isEdit: reservationIdがあればtrue
  const isEdit = ref(!!reservationId)
  
  // ============ リスト類 ============
  const rankOptions = ref([])
  const storeOptions = ref([])
  const storeUserOptions = ref([])
  const menuOptions = ref([])
  
  // ============ フォームデータ ============
  const selectedStoreId = ref(null)
  
  const formData = ref({
	store_user: null,
	start_time: '',
	time_minutes: 60,
	menus: [],
	enrollment_fee: false,
	photo_nomination_fee: false,
	reservation_amount: 0
  })
  
  // ============ マウント時 ============
  onMounted(async () => {
	// 1) ランク一覧
	await fetchRanks()
	// 2) 店舗
	await fetchStores()
	// 3) メニュー
	await fetchMenus()
  
	// 4) もしreservationIdがあれば→既存データを取得し、フォームに反映
	if (isEdit.value) {
	  await fetchReservation(reservationId)
	}
  })
  
  // ============ API呼び出し ============
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
	} catch (err) {
	  console.error('店舗一覧取得失敗', err)
	}
  }
  // メニュー一覧
  async function fetchMenus() {
	try {
	  const { data } = await api.get('/reservations/menus/')
	  menuOptions.value = data
	} catch (err) {
	  console.error('メニュー一覧取得失敗', err)
	}
  }
  // StoreUser一覧 (店舗切り替え時)
  async function fetchStoreUsers() {
	if (!selectedStoreId.value) {
	  storeUserOptions.value = []
	  formData.value.store_user = null
	  return
	}
	try {
	  const { data } = await api.get(`/accounts/store-users/?store=${selectedStoreId.value}`)
	  storeUserOptions.value = data
	  // もし既に選択済みのstore_userが新リストに存在しない場合はnullに
	  if (!data.find(su => su.id === formData.value.store_user)) {
		formData.value.store_user = null
	  }
	} catch (err) {
	  console.error('StoreUser一覧取得失敗', err)
	}
  }
  
  // ============ 既存予約を取得 (編集モード) ============
  async function fetchReservation(id) {
	try {
	  const { data } = await api.get(`/reservations/${id}/`)
	  // data内にある store, store_user などを formData に反映
	  // もしサーバーが store_user を返していない場合は別途工夫が必要
	  // ↓サンプル例
	  formData.value.start_time = data.start_time || ''
	  formData.value.time_minutes = data.time_minutes || 60
	  formData.value.menus = data.menus ? data.menus.map(m => m.id) : []
	  formData.value.enrollment_fee = data.enrollment_fee
	  formData.value.photo_nomination_fee = data.photo_nomination_fee
	  formData.value.reservation_amount = data.reservation_amount || 0
  
	  // 店舗ID
	  if (data.store) {
		selectedStoreId.value = data.store.id
		// storeUser一覧を取得
		await fetchStoreUsers()
	  }
  
	  // store_user がサーバーから返る想定なら formData.value.store_user = data.store_user
	  // もし既存APIが store_user を返していない場合は、代わりに store & cast でどうにかするなど工夫
	  // 例:
	  // if (data.store_user) {
	  //   formData.value.store_user = data.store_user.id
	  // }
  
	} catch (err) {
	  console.error('予約詳細取得失敗', err)
	}
  }
  
  // ============ 計算処理 ============
  function calcReservation() {
	let total = 0
  
	// メニュー加算
	formData.value.menus.forEach(mId => {
	  const mObj = menuOptions.value.find(x => x.id === mId)
	  if (mObj) total += Number(mObj.price) || 0
	})
  
	// 入会金など
	if (formData.value.enrollment_fee) {
	  total += 5000
	}
	if (formData.value.photo_nomination_fee) {
	  total += 2000
	}
  
	// ランク (StoreUser) 加算
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
		// 星数
		const starCount = chosenSU.star_count || 0
		total += starCount * chosenRank.plus_per_star
	  }
	}
  
	formData.value.reservation_amount = total
	console.log("計算結果:", total)
  }
  
  // ============ 保存処理 (Create or Update) ============
  async function saveReservation() {
	try {
	  const payload = { ...formData.value }
  
	  if (isEdit.value) {
		// 編集モード: PUT /reservations/:id/
		await api.put(`/reservations/${reservationId}/`, payload)
		alert('予約を更新しました')
	  } else {
		// 新規モード: POST /reservations/
		await api.post('/reservations/', payload)
		alert('予約を作成しました')
	  }
  
	  router.push('/reservations') // 一覧へ
	} catch (err) {
	  console.error('予約保存失敗', err)
	  alert('保存に失敗しました')
	}
  }
  </script>
  