<script setup>
import { ref, watch, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  getStores, getCustomers, getDrivers, getCourses,
  getCastProfiles, getPrice,
  createReservation, updateReservation, getReservation
} from '@/api';

const route  = useRoute();
const router = useRouter();
const isEdit = !!route.params.id;

/* ---------- フォーム ---------- */
const form = ref({
  store: '', cast_profile: '', start_at: '', course: '',
  driver: '', customer: ''
});

/* ---------- 画面用 ---------- */
const price = ref(0);
const opts  = ref({
  stores: [], customers: [], drivers: [],
  courses: [], casts: []
});

/* ---------- 初期ロード ---------- */
const fetchMasters = async () => {
  const [stores, customers, drivers, courses] = await Promise.all([
    getStores(), getCustomers(), getDrivers(), getCourses()
  ]);
  opts.value = { stores, customers, drivers, courses, casts: [] };
  if (!isEdit) form.value.store = stores[0]?.id ?? '';
};

const fetchReservation = async () => {
  if (!isEdit) return;
  const r = await getReservation(route.params.id);
  Object.assign(form.value, {
    store:        r.store,
    cast_profile: r.casts[0]?.cast_profile ?? '',
    start_at:     r.start_at.slice(0, 16),
    course:       r.casts[0]?.rank_course ?? '',
    driver:       r.driver,
    customer:     r.customer,
  });
};

const fetchCasts = async () => {
  opts.value.casts = await getCastProfiles();   // 全キャスト
};

watch([() => form.value.cast_profile, () => form.value.course], async ([cp, crs]) => {
  price.value = (cp && crs) ? await getPrice(cp, crs) : 0;
});

onMounted(async () => {
  await fetchMasters();
  await fetchReservation();
  await fetchCasts();
});

const save = async () => {
  const payload = {
    store: form.value.store,
    driver: form.value.driver || null,
    customer: form.value.customer || null,
    start_at: new Date(form.value.start_at).toISOString(),
    total_time: opts.value.courses.find(c => c.id === form.value.course)?.minutes ?? 0,
    casts: [{ cast_profile: form.value.cast_profile, rank_course: form.value.course }]
  };
  isEdit
    ? await updateReservation(route.params.id, payload)
    : await createReservation(payload);

  router.push('/reservations');
};
</script>

<template>
  <div class="container py-4">
    <h1 class="h3 mb-4">
      {{ isEdit ? `予約 #${route.params.id} 編集` : '新規予約' }}
    </h1>

    <div class="row gy-3">
      <!-- 店舗 -->
      <div class="col-12">
        <label class="form-label">店舗</label>
        <select v-model="form.store" class="form-select">
          <option v-for="s in opts.stores" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>

      <!-- キャスト -->
      <div class="col-12">
        <label class="form-label">キャスト</label>
        <div class="list-group">
          <label v-for="c in opts.casts" :key="c.id"
                 class="list-group-item list-group-item-action d-flex align-items-center gap-2"
                 :class="{ active: form.cast_profile === c.id }">
            <input class="form-check-input mt-0"
                   type="radio"
                   v-model.number="form.cast_profile"
                   :value="c.id" />
            <span>{{ c.stage_name }}（☆{{ c.star_count }}）</span>
          </label>
        </div>
      </div>

      <!-- 開始日時 -->
      <div class="col-md-6">
        <label class="form-label">開始日時</label>
        <input type="datetime-local" v-model="form.start_at" class="form-control" />
      </div>

      <!-- コース -->
      <div class="col-md-6">
        <label class="form-label">コース</label>
        <select v-model="form.course" class="form-select">
          <option v-for="c in opts.courses" :key="c.id" :value="c.id">
            {{ c.minutes }}min {{ c.is_pack ? '（パック）' : '' }}
          </option>
        </select>
      </div>

      <!-- ドライバー -->
      <div class="col-md-6">
        <label class="form-label">ドライバー</label>
        <select v-model="form.driver" class="form-select">
          <option value="">― 未指定 ―</option>
          <option v-for="d in opts.drivers" :key="d.id" :value="d.id">
            {{ d.name }}
          </option>
        </select>
      </div>

      <!-- 顧客 -->
      <div class="col-md-6">
        <label class="form-label">顧客</label>
        <select v-model="form.customer" class="form-select">
          <option value="">― 未指定 ―</option>
          <option v-for="c in opts.customers" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>

      <!-- 見積 -->
      <div class="col-12">
        <div class="alert alert-info">
          現在の見積 <strong>{{ price.toLocaleString() }}</strong> 円
        </div>
      </div>

      <div class="col-12 text-end">
        <button class="btn btn-primary" @click="save">保存</button>
      </div>
    </div>
  </div>
</template>
