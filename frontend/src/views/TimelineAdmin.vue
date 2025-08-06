<!-- src/views/TimelineAdmin.vue -->

<script setup>
import { ref, watch, onMounted } from 'vue'
import VueCal                     from 'vue-cal'
import 'vue-cal/dist/vuecal.css'

import { getStores }              from '@/api'         // 既存を流用
import { api }                    from '@/api'         // 直で呼ぶ

/* ---------- フィルター状態 ---------- */
const date  = ref(new Date().toISOString().slice(0,10))   // YYYY-MM-DD
const store = ref('')

/* ---------- マスタ ---------- */
const stores = ref([])
onMounted(async () => {
  stores.value = await getStores()
  store.value  = stores.value[0]?.id ?? ''
})

/* ---------- 予約取得 ---------- */
const events = ref([])

const fetchEvents = async () => {
  if (!store.value) return
  const res = await api.get('reservations/', {
    params:{ date: date.value, store: store.value }
  })
  events.value = res.data.map(r => ({
    title : `${r.cast_names.join(', ')} / ${r.status}`,
    start : new Date(r.start_at),
    end   : new Date(new Date(r.start_at).getTime() + r.total_time*60000),
    data  : r
  }))
}

/* 初期 & フィルター変更で再取得 */
watch([date, store], fetchEvents, { immediate:true })

/* ---------- クリック時に編集ページへ ---------- */
import { useRouter } from 'vue-router'
const router = useRouter()
const onClick = ({ event }) =>
  router.push({ name:'reservation-detail', params:{ id: event.data.id } })
</script>


<template>
  <div class="container py-4">
    <h1 class="h4 mb-3">
      予約タイムライン（管理者）
    </h1>

    <!-- フィルター -->
    <div class="d-flex gap-3 mb-3">
      <input
        v-model="date"
        type="date"
        class="form-control"
        style="max-width:180px"
      >

      <select
        v-model="store"
        class="form-select"
        style="max-width:220px"
      >
        <option
          disabled
          value=""
        >
          店舗を選択
        </option>
        <option
          v-for="s in stores"
          :key="s.id"
          :value="s.id"
        >
          {{ s.name }}
        </option>
      </select>
    </div>

    <!-- カレンダー -->
    <vue-cal
      v-if="events.length"
      :events="events"
      :time="true"
      :on-event-click="onClick"
      style="height: 70vh"
    />

    <p
      v-else
      class="text-muted"
    >
      予約なし
    </p>
  </div>
</template>


<style>
/* vue-cal の枠をブートストラップ調に */
.vuecal {
  --vuecal-selected: #0d6efd33;
  --vuecal-primary  : #0d6efd;
}
</style>
