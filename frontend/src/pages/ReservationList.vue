<template>
  <div class="reservation reservation__list container">
    <h2>予約一覧</h2>

    <!-- <div class="menu">
      <div class="area">
        <button @click="$router.push('/dashboard/reservations/create')">
          <i class="fas fa-plus-circle"></i>予約作成
        </button>
      </div>
    </div> -->

    <!-- 参考 -->
    <div class="reservation-list d-none">
      <div class="grid">
        <div class="head">
          <div class="head__inner cell">ID</div>
          <div class="head__inner cell">予約名</div>
          <div class="head__inner cell">店舗</div>
          <div class="head__inner cell">キャスト</div>
          <div class="head__inner cell">ドライバー</div>
          <div class="head__inner cell">開始時刻</div>
          <div class="head__inner cell">予約時間(分)</div>
          <div class="head__inner cell">メニュー</div>
          <div class="head__inner cell">入会金</div>
          <div class="head__inner cell">入会金0円</div>
          <div class="head__inner cell">写真指名</div>
          <div class="head__inner cell">写真指名0円</div>
          <div class="head__inner cell">本指名</div>
          <div class="head__inner cell">本指名割引</div>
          <div class="head__inner cell">キャスト受取</div>
          <div class="head__inner cell">ドライバー受取</div>
          <div class="head__inner cell">店舗受取</div>
          <div class="head__inner cell">予約金額</div>
          <div class="head__inner cell">詳細</div>
        </div>

        <div class="value__outer">
          <!-- 予約データを繰り返し表示 -->
          <div class="value" v-for="reservation in reservations" :key="reservation.id">
            <div class="value__inner cell">{{ reservation.id }}</div>

            <!-- 予約名 -->
            <div class="value__inner cell">
              {{ reservation.customer_name }}
            </div>

            <!-- 店舗 -->
            <div class="value__inner cell">
              <!-- GET時のserializer次第で store が null の場合もありうる -->
              <template v-if="reservation.store">
                {{ reservation.store.name }}
              </template>
              <template v-else>
                未選択
              </template>
            </div>

            <!-- キャスト -->
            <div class="value__inner cell">
              <template v-if="reservation.cast">
                {{ reservation.cast.full_name }}
              </template>
              <template v-else>
                未定
              </template>
            </div>

            <!-- ドライバー -->
            <div class="value__inner cell">
              <template v-if="reservation.driver">
                {{ reservation.driver.full_name }}
              </template>
              <template v-else>
                未定
              </template>
            </div>

            <!-- 開始時刻 -->
            <div class="value__inner cell">
              {{ reservation.start_time }}
            </div>

            <!-- 予約時間(分) -->
            <div class="value__inner cell">
              {{ reservation.time_minutes }}
            </div>

            <!-- メニュー (多対多で array) -->
            <div class="value__inner cell">
              <template v-if="reservation.menus && reservation.menus.length">
                <ul>
                  <li
                    v-for="menuItem in reservation.menus"
                    :key="menuItem.id"
                  >
                    {{ menuItem.name }} ({{ menuItem.price }}円)
                  </li>
                </ul>
              </template>
              <template v-else>
                なし
              </template>
            </div>

            <!-- 入会金 -->
            <div class="value__inner cell">
              <template v-if="reservation.enrollment_fee">
                あり
              </template>
              <template v-else>
                なし
              </template>
            </div>

            <!-- 入会金0円 -->
            <div class="value__inner cell">
              <template v-if="reservation.enrollment_fee_discounted">
                適用
              </template>
              <template v-else>
                -
              </template>
            </div>

            <!-- 写真指名 -->
            <div class="value__inner cell">
              <template v-if="reservation.photo_nomination_fee">
                あり
              </template>
              <template v-else>
                なし
              </template>
            </div>

            <!-- 写真指名0円 -->
            <div class="value__inner cell">
              <template v-if="reservation.photo_nomination_fee_discounted">
                適用
              </template>
              <template v-else>
                -
              </template>
            </div>

            <!-- 本指名 -->
            <div class="value__inner cell">
              <template v-if="reservation.regular_nomination_fee">
                あり
              </template>
              <template v-else>
                なし
              </template>
            </div>

            <!-- 本指名割引 -->
            <div class="value__inner cell">
              <template v-if="reservation.regular_nomination_fee_discounted">
                適用
              </template>
              <template v-else>
                -
              </template>
            </div>

            <!-- キャスト受取 -->
            <div class="value__inner cell">
              {{ reservation.cast_received }} 円
            </div>

            <!-- ドライバー受取 -->
            <div class="value__inner cell">
              {{ reservation.driver_received }} 円
            </div>

            <!-- 店舗受取 -->
            <div class="value__inner cell">
              {{ reservation.store_received }} 円
            </div>

            <!-- 予約金額 -->
            <div class="value__inner cell">
              {{ reservation.reservation_amount }} 円
            </div>

            <!-- 詳細ボタン -->
            <div class="value__inner cell">
              <button
                @click="$router.push(`/dashboard/reservations/${reservation.id}`)"
              >
                詳細
              </button>
            </div>
          </div>
        </div> <!-- value__outer -->
      </div><!-- grid -->
    </div> <!-- reservation-list -->

    <!-- 新規 -->
    <div class="reservation__list--wrap">

      <div class="area" v-for="reservation in reservations" :key="reservation.id">
        <div class="box contents">
          <div class="head">
            <div class="cast">
              <div class="photo" v-if="reservation.cast">
                <router-link :to="`/dashboard/reservations/${reservation.id}`">
                  <img
                    v-if="reservation.cast.cast_photo"
                    :src="reservation.cast.cast_photo"
                    alt="Cast photo"
                  />
                  <img
                    v-else
                    src="/noimage.webp"
                    alt=""
                  />
                </router-link>
              </div>
              <div class="name">{{ reservation.cast.full_name }}</div>
            </div>
            <div class="staff">
              <div class="id">{{ reservation.id }}</div>
              <div class="driver">{{ reservation.driver.full_name }}</div>
              <div class="store">{{ reservation.store.name }}</div>
            </div>
          </div>
          <div class="customer">
            <div class="grid-1 grid">
              <div class="name">{{ reservation.customer_name }}</div>
              <div class="adress">{{ reservation.postal_code }} {{ reservation.address }}</div>
            </div>
            <div class="grid-2 grid">
              <div class="option">
                <template v-if="reservation.menus && reservation.menus.length">
                    <ul>
                      <li
                        v-for="menuItem in reservation.menus"
                        :key="menuItem.id"
                      >
                        {{ menuItem.name }}
                      </li>
                    </ul>
                  </template>
                <template v-else>
                  なし
                </template>
              </div>
            </div>
            <div class="grid-3 grid">
              <div class="start">{{ formatDateTime(reservation.start_time) }}</div>
              <div class="time">{{ reservation.time_minutes }}</div>
              <div class="amount">{{ reservation.reservation_amount }}</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div><!-- container -->
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api';

const reservations = ref([]);
const router = useRouter();

// 予約一覧を取得
const fetchReservations = async () => {
  try {
    // /reservations/ にGETリクエスト
    const response = await api.get('/reservations/');
    // IDが新しい順にソート
    reservations.value = response.data.sort((a, b) => b.id - a.id);
  } catch (error) {
    console.error('予約データの取得に失敗:', error);
  }
};

function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)  // ISO8601文字列からDateを生成
  const yyyy = date.getFullYear()
  const mm = ('0' + (date.getMonth() + 1)).slice(-2)
  const dd = ('0' + date.getDate()).slice(-2)
  const hh = ('0' + date.getHours()).slice(-2)
  const mi = ('0' + date.getMinutes()).slice(-2)
  // "2025-03-10 19:56" のように組み立てる
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
}

// 詳細ページへ移動
const goToDetail = (id) => {
  router.push(`/dashboard/reservations/${id}`);
};

// 編集ページへ移動（もし使うなら）
const goToEdit = (id) => {
  router.push(`/dashboard/reservations/${id}/edit`);
};

onMounted(fetchReservations);
</script>
