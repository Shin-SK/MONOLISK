<script setup>
import { ref, watch }        from 'vue'
import VueCal                from 'vue-cal'
import 'vue-cal/dist/vuecal.css'
import { api }               from '@/api'

const date   = ref(new Date().toISOString().slice(0,10))
const events = ref([])

const fetchEvents = async () => {
  const { data } = await api.get('reservations/mine/', {
    params:{ date: date.value }
  })
  events.value = data.map(r => ({
    title : `${r.status} / ${r.store_name}`,
    start : new Date(r.start_at),
    end   : new Date(new Date(r.start_at).getTime() + r.total_time*60000),
    data  : r
  }))
}
watch(date, fetchEvents, { immediate:true })
</script>

<template>
<div class="container py-4">
  <h1 class="h5 mb-3">私のタイムライン</h1>
  <input type="date" v-model="date" class="form-control mb-3" style="max-width:180px">
  <vue-cal :events="events" :time="true" style="height:70vh" />
</div>
</template>
