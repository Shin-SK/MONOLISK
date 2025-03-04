
<template>
  <div class="reservation reservation__list container">
    <h2>予約一覧</h2>

    <div class="menu">
      <div class="area">
        <button @click="$router.push(`/dashboard/reservations/create/`)"><i class="fas fa-plus-circle"></i>予約作成</button>
      </div>
    </div>

    <div class="reservation-list">

      <div class="grid">
        <div class="head">
          <div class="head__inner cell">ID</div>
          <div class="head__inner cell">予約名</div>
          <div class="head__inner cell">キャスト</div>
          <div class="head__inner cell">コース</div>
          <div class="head__inner cell">料金</div>
          <div class="head__inner cell">ドライバー</div>
          <div class="head__inner cell">詳細</div>
        </div>
        <div class="value__outer">
          <div class="value" v-for="reservation in reservations" :key="reservation.id">
            <div class="value__inner cell">{{ reservation.id }}</div>
            <div class="value__inner cell">{{ reservation.customer_name }}</div>
            <div class="value__inner cell">{{ reservation.cast ? reservation.cast.full_name : '未定' }}</div>
            <div class="value__inner cell">{{ reservation.course ? reservation.course.name : '未選択' }}</div>
            <div class="value__inner cell">{{ reservation.reservation_amount }}円</div>
            <div class="value__inner cell">{{ reservation.driver ? reservation.driver.full_name : '未定' }}</div>
            <div class="value__inner cell">
              <button @click="$router.push(`/dashboard/reservations/${reservation.id}`)">詳細</button>
            </div>
          </div>
        </div>
      </div><!-- grid -->

    </div>
  </div><!-- container -->

</template>


<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api';

const reservations = ref([]);
const router = useRouter();

const fetchReservations = async () => {
  try {
    const response = await api.get('/reservations/');
    reservations.value = response.data;
  } catch (error) {
    console.error('予約データの取得に失敗:', error);
  }
};

const goToDetail = (id) => {
  router.push(`/reservations/${id}`);
};

const goToEdit = (id) => {
  router.push(`/reservations/${id}/edit`);
};

onMounted(fetchReservations);
</script>
