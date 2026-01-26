<script setup>
import { onMounted } from 'vue'
import dayjs from 'dayjs'
import { useNominationSummaries } from '@/composables/useNominationSummaries'

const props = defineProps({
  billId: {
    type: Number,
    required: true
  }
})

const { loading, error, results, fetchNominationSummaries } = useNominationSummaries()

onMounted(() => {
  if (props.billId) {
    fetchNominationSummaries(props.billId)
  }
})

const formatDate = (dateStr) => {
  return dateStr ? dayjs(dateStr).format('HH:mm') : '—'
}

const formatPeriodStatus = (status) => {
  return status === 'ongoing' ? '進行中' : '終了'
}

const formatMoney = (num) => {
  return `¥${(Number(num || 0)).toLocaleString()}`
}
</script>

<template>
  <div class="nomination-summary-panel mt-4">
    <!-- ローディング -->
    <div v-if="loading" class="d-flex justify-content-center py-3">
      <div class="spinner-border spinner-border-sm text-primary" role="status">
        <span class="visually-hidden">読み込み中...</span>
      </div>
    </div>

    <!-- エラー -->
    <div v-else-if="error" class="alert alert-warning alert-dismissible fade show" role="alert">
      <strong>本指名サマリー読み込みエラー</strong><br />
      {{ error.message || '詳細は不明' }}
      <button
        type="button"
        class="btn-close"
        data-bs-dismiss="alert"
        aria-label="Close"
      ></button>
    </div>

    <!-- 結果が空 -->
    <div v-else-if="!results || results.length === 0" class="alert alert-info" role="alert">
      本指名期間の卓小計データはありません
    </div>

    <!-- 結果表示 -->
    <div v-else class="card">
      <div class="card-header bg-light">
        <h6 class="mb-0">本指名期間の卓小計</h6>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-sm table-hover mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 60px">顧客ID</th>
                <th style="width: 80px">期間</th>
                <th style="width: 60px">ステータス</th>
                <th style="width: 100px">卓小計</th>
                <th style="width: 80px">人数</th>
                <th style="width: 100px">1人当たり</th>
                <th style="width: 100px">キャスト</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in results" :key="item.customer_id">
                <td class="fw-bold">{{ item.customer_id }}</td>
                <td class="text-muted small">
                  {{ formatDate(item.period_start) }} ～<br />
                  {{ formatDate(item.period_end) }}
                </td>
                <td>
                  <span
                    v-if="item.period_status === 'ongoing'"
                    class="badge bg-warning text-dark"
                  >
                    進行中
                  </span>
                  <span v-else class="badge bg-secondary">終了</span>
                </td>
                <td class="text-end fw-bold">
                  {{ formatMoney(item.subtotal) }}
                </td>
                <td class="text-center">
                  {{ item.num_casts }}
                </td>
                <td class="text-end">
                  {{ formatMoney(item.per_cast_share) }}
                </td>
                <td class="small text-muted">
                  {{ (item.cast_ids || []).join(', ') || '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nomination-summary-panel {
  font-size: 0.9rem;
}

.nomination-summary-panel .table {
  margin-bottom: 0;
}

.nomination-summary-panel .table td {
  padding: 0.5rem;
  vertical-align: middle;
}
</style>
