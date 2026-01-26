<script setup>
import { ref, onMounted, computed } from 'vue'
import dayjs from 'dayjs'
import { useBillCustomers } from '@/composables/useBillCustomers'
import { useBillCustomerTimeline } from '@/composables/useBillCustomerTimeline'
import { useNominations } from '@/composables/useNominations'
import { useCasts } from '@/stores/useCasts'
import { api } from '@/api'

const props = defineProps({
  billId: {
    type: Number,
    required: true
  }
})

// Composables
const billCustomersComposable = useBillCustomers()
const timelineComposable = useBillCustomerTimeline()
const nominationsComposable = useNominations()
const castsStore = useCasts()

// Local state
const casts = ref([])
const selectedCastsByCustomer = ref({})  // { customer_id: [cast_id, ...] }
const loadingNominations = ref(false)

onMounted(async () => {
  // キャスト一覧を取得
  await castsStore.refresh?.()
  casts.value = castsStore.list?.value || []
})

// billId が変わったら再読み込み
const reload = async (billId) => {
  if (!billId) return
  
  await billCustomersComposable.fetchBillCustomers(billId)
  await nominationsComposable.fetchNominations(billId)
  
  // nominations から customer_id → [cast_ids] にグルーピング
  const grouped = {}
  nominationsComposable.nominations.value?.forEach(nom => {
    if (!grouped[nom.customer_id]) {
      grouped[nom.customer_id] = []
    }
    if (nom.cast_id) {
      grouped[nom.customer_id].push(nom.cast_id)
    }
  })
  selectedCastsByCustomer.value = grouped
}

// billId watcher
import { watch } from 'vue'
watch(() => props.billId, (billId) => {
  reload(billId)
}, { immediate: true })

/**
 * 顧客を追加（arrived_at = now）
 */
const addCustomer = async () => {
  const customerId = prompt('顧客IDを入力してください:')
  if (!customerId) return
  
  try {
    await api.post(`/billing/bills/${props.billId}/customers/`, {
      customer_id: Number(customerId),
      arrived_at: dayjs().toISOString()
    })
    
    // 再読み込み
    await reload(props.billId)
  } catch (e) {
    alert('顧客追加に失敗しました: ' + e.message)
  }
}

/**
 * IN ボタン：arrived_at = now
 */
const handleArrived = async (billCustomerId) => {
  await timelineComposable.markArrived(billCustomerId)
  await reload(props.billId)
}

/**
 * OUT ボタン：left_at = now
 */
const handleLeft = async (billCustomerId) => {
  await timelineComposable.markLeft(billCustomerId)
  await reload(props.billId)
}

/**
 * OUT解除：left_at = null
 */
const handleClearLeft = async (billCustomerId) => {
  await timelineComposable.clearLeft(billCustomerId)
  await reload(props.billId)
}

/**
 * 本指名キャスト選択を変更＆保存
 */
const handleNominationChange = async (customerId) => {
  const castIds = selectedCastsByCustomer.value[customerId] || []
  
  loadingNominations.value = true
  try {
    await nominationsComposable.setNominations(props.billId, customerId, castIds)
  } catch (e) {
    alert('本指名設定に失敗しました: ' + e.message)
  } finally {
    loadingNominations.value = false
  }
}

/**
 * 顧客の本指名キャストをトグル
 */
const toggleNominationCast = (customerId, castId) => {
  if (!selectedCastsByCustomer.value[customerId]) {
    selectedCastsByCustomer.value[customerId] = []
  }
  
  const arr = selectedCastsByCustomer.value[customerId]
  const idx = arr.indexOf(castId)
  
  if (idx >= 0) {
    arr.splice(idx, 1)
  } else {
    arr.push(castId)
  }
}

/**
 * 時刻フォーマット
 */
const fmt = (dt) => dt ? dayjs(dt).format('HH:mm') : '—'

/**
 * ステータス表示
 */
const getStatus = (bc) => {
  if (!bc.arrived_at) return '未IN'
  if (bc.left_at) return '退店済み'
  return 'IN中'
}

const getStatusBadgeClass = (bc) => {
  if (!bc.arrived_at) return 'bg-secondary'
  if (bc.left_at) return 'bg-danger'
  return 'bg-success'
}
</script>

<template>
  <div class="table-customers-panel mt-4">
    <div class="card">
      <div class="card-header bg-light d-flex justify-content-between align-items-center">
        <h6 class="mb-0">テーブル内の顧客</h6>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="addCustomer">
          + 顧客追加
        </button>
      </div>

      <div class="card-body p-0">
        <!-- 顧客一覧 -->
        <div v-if="billCustomersComposable.customers.value?.length" class="list-group list-group-flush">
          <div
            v-for="bc in billCustomersComposable.customers.value"
            :key="bc.id"
            class="list-group-item p-3"
          >
            <!-- 基本情報 -->
            <div class="d-flex justify-content-between align-items-center mb-2">
              <div>
                <strong>{{ bc.display_name }}</strong>
                <span :class="['badge', getStatusBadgeClass(bc)]">{{ getStatus(bc) }}</span>
              </div>
              <small class="text-muted">
                IN: {{ fmt(bc.arrived_at) }} / OUT: {{ fmt(bc.left_at) }}
              </small>
            </div>

            <!-- IN/OUT ボタン -->
            <div class="d-flex gap-2 mb-2">
              <button
                v-if="!bc.arrived_at"
                type="button"
                class="btn btn-sm btn-success"
                @click="handleArrived(bc.id)"
                :disabled="timelineComposable.loading.value"
              >
                IN
              </button>
              <button
                v-if="bc.arrived_at && !bc.left_at"
                type="button"
                class="btn btn-sm btn-warning"
                @click="handleLeft(bc.id)"
                :disabled="timelineComposable.loading.value"
              >
                OUT
              </button>
              <button
                v-if="bc.left_at"
                type="button"
                class="btn btn-sm btn-secondary"
                @click="handleClearLeft(bc.id)"
                :disabled="timelineComposable.loading.value"
              >
                OUT解除
              </button>
            </div>

            <!-- 本指名キャスト設定（仮UI） -->
            <div class="border-top pt-2">
              <small class="text-muted d-block mb-2">本指名キャスト</small>
              <div class="d-flex flex-wrap gap-2 mb-2">
                <div
                  v-for="cast in casts"
                  :key="cast.id"
                  class="form-check form-check-inline"
                >
                  <input
                    type="checkbox"
                    :id="`cast-${bc.id}-${cast.id}`"
                    class="form-check-input"
                    :checked="(selectedCastsByCustomer[bc.customer_id] || []).includes(cast.id)"
                    @change="toggleNominationCast(bc.customer_id, cast.id)"
                  />
                  <label :for="`cast-${bc.id}-${cast.id}`" class="form-check-label small">
                    {{ cast.stage_name }}
                  </label>
                </div>
              </div>
              <button
                type="button"
                class="btn btn-sm btn-primary"
                @click="handleNominationChange(bc.customer_id)"
                :disabled="loadingNominations"
              >
                保存
              </button>
            </div>
          </div>
        </div>

        <!-- 顧客がない場合 -->
        <div v-else class="p-3 text-center text-muted small">
          顧客がまだ登録されていません
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.table-customers-panel {
  font-size: 0.9rem;
}

.list-group-item {
  background-color: #fafafa;
}

.list-group-item:nth-child(odd) {
  background-color: #fff;
}
</style>
