/* src/composables/useBillCustomerTimeline.js */
import { ref } from 'vue'
import { api } from '@/api'
import dayjs from 'dayjs'

/**
 * BillCustomer の arrived_at/left_at を管理
 * 
 * 返すもの：
 * {
 *   loading: ref(false),
 *   error: ref(null),
 *   markArrived: async (billCustomerId) => void,
 *   markLeft: async (billCustomerId) => void,
 *   clearLeft: async (billCustomerId) => void
 * }
 */
export function useBillCustomerTimeline() {
  const loading = ref(false)
  const error = ref(null)

  /**
   * 顧客を「IN」（arrived_at = now）
   */
  async function markArrived(billCustomerId) {
    loading.value = true
    error.value = null

    try {
      const now = dayjs().toISOString()
      await api.patch(`/billing/bill-customers/${billCustomerId}/`, {
        arrived_at: now
      })
    } catch (e) {
      console.error('[useBillCustomerTimeline.markArrived]', e)
      error.value = e
    } finally {
      loading.value = false
    }
  }

  /**
   * 顧客を「OUT」（left_at = now）
   */
  async function markLeft(billCustomerId) {
    loading.value = true
    error.value = null

    try {
      const now = dayjs().toISOString()
      await api.patch(`/billing/bill-customers/${billCustomerId}/`, {
        left_at: now
      })
    } catch (e) {
      console.error('[useBillCustomerTimeline.markLeft]', e)
      error.value = e
    } finally {
      loading.value = false
    }
  }

  /**
   * left_at を解除（null に戻す）
   */
  async function clearLeft(billCustomerId) {
    loading.value = true
    error.value = null

    try {
      await api.patch(`/billing/bill-customers/${billCustomerId}/`, {
        left_at: null
      })
    } catch (e) {
      console.error('[useBillCustomerTimeline.clearLeft]', e)
      error.value = e
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    markArrived,
    markLeft,
    clearLeft
  }
}
