<!-- src/views/TimelineDriver.vue -->
<script setup>
import { ref, watch }  from 'vue'
import VueCal          from 'vue-cal'
import 'vue-cal/dist/vuecal.css'
import { api }         from '@/api'

const date   = ref(new Date().toISOString().slice(0,10))
const events = ref([])

const fetchEvents = async () => {
  const { data } = await api.get('reservations/mine-driver/', {
    params:{ date: date.value }
  })
  events.value = data.map(r => ({
    title : `${r.customer_name} / ${r.status}`,
    start : new Date(r.start_at),
    end   : new Date(new Date(r.start_at).getTime() + r.total_time*60000),
    data  : r
  }))
}
watch(date, fetchEvents, { immediate:true })

/* クリックで詳細（ドライバー用フォーム）に遷移 */
import { useRouter } from 'vue-router'
const router = useRouter()
const onClick = ({ event }) =>
  router.push({ name:'reservation-detail', params:{ id:event.data.id } })
</script>

<template>
<div class="container py-4">
  <h1 class="h5 mb-3">私の配車スケジュール</h1>
  <input type="date" v-model="date" class="form-control mb-3" style="max-width:180px">
  <vue-cal :events="events" :time="true" :on-event-click="onClick" style="height:70vh" />
</div>
</template>

<style>
.vuecal {
  --vuecal-selected:#0d6efd33;
  --vuecal-primary :#0d6efd;
}
</style>
