
<template>
  <div class="reservation__detail">
    <h2>予約フォーム {{ reservationId ? '（編集）' : '（新規）' }}</h2>

    <!-- 店舗選択 -->
    <div class="area radio store">
      <div class="head">店舗</div>
      <div class="value">
        <div class="value__inner" v-for="store in stores" :key="store.id">
          <input 
            type="radio" 
            v-model="selectedStoreId" 
            :id="'radio-' + store.id"
            :value="store.id"
            @change="handleStoreChange"
            class="radio-button"
          />
          <label :for="'radio-' + store.id" class="radio-label">
            {{ store.name }}
          </label>
        </div>
      </div>
    </div>

    <!-- キャスト選択 -->
    <div class="area radio cast">
      <div class="head">キャスト</div>
      <div class="value">
        <div class="value__inner" v-for="cast in casts" :key="cast.user_id">
          <input
            type="radio"
            v-model="selectedCastId"
            :id="'radio-cast-' + cast.user_id"
            :value="cast.user_id"
            :disabled="!casts.length"
            class="radio-button"
            @change="handleCastChange"
          />
          <label :for="'radio-cast-' + cast.user_id" class="radio-label">
            {{ cast.nickname }}
          </label>
        </div>
      </div>
    </div>


    <!-- 顧客名 -->
    <div class="area text">
      <div class="head">ご予約名</div>
      <div class="box">
        <div class="current-value">{{ customerName }}</div>
        <input v-model="customerName" type="text" class="text"/>
      </div>
    </div>

    <!-- 開始時間 -->
    <div class="area calendar">
      <div class="head">開始時間</div>
      <div class="box">
        <div class="current-value">{{ startTime }}</div>
        <input v-model="startTime" type="datetime-local" />
      </div>
    </div>

    <!-- 保存ボタン -->
    <button class="submit" @click="saveReservation">
      {{ reservationId ? '更新' : '作成' }}
    </button>
  </div><!-- reservation__detail -->
</template>



<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/api';

const route = useRoute();
const router = useRouter();

// URLパラメータのid。無い場合は新規作成モード
const reservationId = route.params.id || null;

// 各種データ
const stores = ref([]);
const casts = ref([]);

// フォーム入力（双方向バインド用）
const selectedStoreId = ref(null);
const selectedCastId = ref(null);
const customerName = ref('');
const startTime = ref(''); // "YYYY-MM-DDTHH:mm" など
// 必要に応じて membership_type, time_minutes なども宣言

// 1) マウント時に店舗一覧を取得
onMounted(async () => {
  await fetchStores();
  
  // 2) 既存予約のIDがある場合は、予約詳細を取得してセット
  if (reservationId) {
    await fetchReservation(reservationId);
  }
});

// 店舗一覧を取得
const fetchStores = async () => {
  try {
    const res = await api.get('/accounts/stores/');
    stores.value = res.data; // [{id, name}, {id, name}, ...]
  } catch (error) {
    console.error('店舗一覧取得失敗:', error);
  }
};

// 選択した店舗に属するキャスト一覧を取得
const fetchCasts = async (storeId) => {
  try {
    const res = await api.get(`/accounts/casts/?store=${storeId}`);
    casts.value = res.data.casts; // [{id, full_name}, ...]
  } catch (error) {
    console.error('キャスト一覧取得失敗:', error);
  }
};

// 店舗が変わったとき
const handleStoreChange = async () => {
  if (!selectedStoreId.value) {
    casts.value = [];
    selectedCastId.value = null;
    return;
  }
  // 店舗に紐づくキャスト一覧を取得
  await fetchCasts(selectedStoreId.value);
  // 編集の場合、既存の cast が存在したら、必要に応じて selectedCastId を合わせる
};

// 既存予約を取得してフォームに反映
const fetchReservation = async (id) => {
  try {
    const { data } = await api.get(`/reservations/${id}/`);
    // 取得したデータをフォームにセット
    customerName.value = data.customer_name;
    startTime.value = data.start_time;

    // 店舗
    if (data.store) {
      selectedStoreId.value = data.store.id;
      // 店舗をセットしたので、キャスト一覧を取得したうえで、cast を反映
      await fetchCasts(data.store.id);
    }
    // キャスト
    if (data.cast) {
      selectedCastId.value = data.cast.id;
    }
    // ほか membership_type, time_minutes なども同様にセット
  } catch (error) {
    console.error('予約詳細取得失敗:', error);
  }
};

// 予約の保存（新規 or 更新）
const saveReservation = async () => {
  const payload = {
    customer_name: customerName.value,
    start_time: startTime.value,
    store: selectedStoreId.value,  // store の ID
    cast: selectedCastId.value,    // cast の ID
    // membership_type, time_minutes なども同様に
  };

  try {
    if (!reservationId) {
      // 新規作成
      const res = await api.post('/reservations/', payload);
      console.log('予約作成成功:', res.data);
      router.push(`/reservations/${res.data.id}`);
    } else {
      // 更新
      const res = await api.put(`/reservations/${reservationId}/`, payload);
      console.log('予約更新成功:', res.data);
      // 必要なら一覧へ戻る or このままページに留まる
      // router.push('/reservations');
    }
  } catch (error) {
    console.error('予約保存失敗:', error);
  }
};
</script>