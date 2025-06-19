<!-- src/views/ReservationFormCast.vue -->
<script setup>
import { ref, onMounted, watch }   from 'vue'
import { useRoute, useRouter }     from 'vue-router'
import { getReservation }         from '@/api'          /* ← 更新 API は不要 */
import { useUser }                 from '@/stores/useUser'

const userStore = useUser()
const router    = useRouter()
const route     = useRoute()

/* ---- 画面切替（タイムライン / リスト） --------------------------- */
const mode = ref('timeline')        // 'timeline' | 'list'

watch(mode, v => {
  if (v === 'timeline') router.push('/cast/mypage')
  else                  router.push('/cast/mypage?view=list')
})

/* ---- 予約取得 ---------------------------------------------------- */
const rsv = ref(null)

async function reload () {
  rsv.value = await getReservation(route.params.id)
}
onMounted(reload)
</script>

<template>
  <div class="container py-4" v-if="rsv">
    <h1 class="h4 mb-4">予約 #{{ rsv.id }}（キャスト）</h1>

    <table class="table">
      <tbody>
        <tr><th>キャスト</th><td>{{ rsv.cast_names.join(', ') }}</td></tr>
        <tr><th>開始</th><td>{{ new Date(rsv.start_at).toLocaleString() }}</td></tr>

        <tr v-if="rsv.course_minutes">
          <th>コース</th>
          <td>{{ rsv.course_minutes }} 分</td>
        </tr>

        <tr v-if="rsv.customer_address">
          <th>住所</th>
          <td>{{ rsv.customer_address }}</td>
        </tr>

        <tr v-if="rsv.charges.length">
          <th>オプション</th>
          <td>
            <span v-for="ch in rsv.charges" :key="ch.id"
                  class="badge bg-secondary me-1">
              {{ ch.option_name }} {{ ch.amount }}円
            </span>
          </td>
        </tr>

        <tr><th>お客様名</th><td>{{ rsv.customer_name }}</td></tr>
        <tr><th>見積</th><td>{{ rsv.expected_amount.toLocaleString() }} 円</td></tr>
      </tbody>
    </table>
  </div>
</template>
