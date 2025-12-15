<!-- src/views/CustomerForm.vue -->
<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CustomerPicker from '@/components/CustomerPicker.vue'

const route = useRoute()
const router = useRouter()

// v-model で CustomerPicker に渡す ID
const pickedId = ref(Number(route.params.id) || null)

watch(
  () => route.params.id,
  v => { pickedId.value = v ? Number(v) : null }
)

function handleSaved(saved) {
  // トーストがあれば出す
  try { window?.$toast?.success?.('保存しました') } catch {}
  // 一覧へ戻す（manager の顧客一覧ルート名）
  router.push({ name: 'mng-customers' })
}
</script>

<template>
  <div class="container py-4">
    <!-- CustomerPicker をそのまま編集フォームとして使う -->
    <CustomerPicker
      v-model="pickedId"
      @saved="handleSaved"
    />

    <button class="mt-3 btn btn-sm btn-outline-secondary" @click="$router.back()">戻る</button>
  </div>
</template>
