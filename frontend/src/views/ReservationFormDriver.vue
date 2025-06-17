<!-- src/views/ReservationFormDriver.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReservation, updateReservation } from '@/api'

const route    = useRoute()
const router   = useRouter()
const rsv      = ref(null)
const received = ref(null)

/* 予約取得 */
async function reload () {
  rsv.value = await getReservation(route.params.id)
  received.value = rsv.value.received_amount
}

onMounted(reload)

/* 保存 */
async function save () {
  await updateReservation(rsv.value.id, { received_amount: received.value })
  await reload()                               // ★ 最新状態を取り直す
  alert('受取金額を更新しました')
  router.push('/driver')                       // 一覧へ戻る
}
</script>



<template>
<div class="container py-4" v-if="rsv">
  <h1 class="h4 mb-4">予約 #{{ rsv.id }}（ドライバー）</h1>

  <table class="table">
    <tbody>
      <tr><th>キャスト</th><td>{{ rsv.cast_names.join(', ') }}</td></tr>
      <tr><th>開始</th><td>{{ new Date(rsv.start_at).toLocaleString() }}</td></tr>
      <tr><th>お客様名</th><td>{{ rsv.customer_name }}</td></tr>
      <tr><th>見積</th><td>{{ rsv.expected_amount.toLocaleString() }} 円</td></tr>
    </tbody>
  </table>

  <div class="mb-3">
    <label class="form-label">受取金額</label>
    <input type="number" class="form-control" v-model.number="received" />
  </div>

  <button class="btn btn-primary" @click="save">保存</button>
</div>
</template>
