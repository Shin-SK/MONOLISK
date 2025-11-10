<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
import { getStoreNotice } from '@/api'

const route = useRoute()
const id = Number(route.params.id)
const data = ref(null)
const loading = ref(false)
const error = ref('')

function fmt(d){ return d ? dayjs(d).format('YYYY/MM/DD HH:mm') : '' }

onMounted(async () => {
  loading.value = true
  try {
    data.value = await getStoreNotice(id)
  } catch (e) {
    error.value = e?.response?.data?.detail || '記事の取得に失敗しました'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container py-4" style="max-width:800px">
    <div v-if="loading" class="text-muted">読み込み中…</div>
    <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-else-if="data">
      <h3 class="mb-1">{{ data.title }}</h3>
      <div class="text-muted mb-3">{{ fmt(data.publish_at || data.created_at) }}</div>
      <img v-if="data.cover_url" :src="data.cover_url" class="rounded m-auto d-block">
      <div class="card mt-4">
        <div class="card-body bg-white" style="white-space:pre-wrap;line-height:1.8;">
          {{ data.body }}
        </div>
      </div>
    </div>
  </div>
</template>
