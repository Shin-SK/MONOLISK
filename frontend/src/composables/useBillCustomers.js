/* src/composables/useBillCustomers.js */
import { ref } from 'vue'
import { api } from '@/api'

/**
 * 伝票の本指名顧客（BillCustomer）一覧を取得
 * 
 * 返すもの：
 * {
 *   loading: ref(false),
 *   error: ref(null),
 *   customers: ref([]),  // { id, customer_id, customer_name, display_name, ... }
 *   fetchBillCustomers: async (billId) => void,
 *   refresh: async (billId) => void
 * }
 */
export function useBillCustomers() {
  const loading = ref(false)
  const error = ref(null)
  const customers = ref([])

  /**
   * billId から顧客一覧を取得
   * @param {number} billId
   */
  async function fetchBillCustomers(billId) {
    loading.value = true
    error.value = null
    customers.value = []

    try {
      const response = await api.get(`/billing/bills/${billId}/customers/`)
      const data = response.data?.results || []
      
      // 整形：display_name がない場合は customer_name を使う
      customers.value = data.map(bc => ({
        id: bc.id,
        customer_id: bc.customer_id,
        customer_name: bc.customer_name || bc.display_name || `顧客 ${bc.customer_id}`,
        display_name: bc.display_name || bc.customer_name || `顧客 ${bc.customer_id}`,
        arrived_at: bc.arrived_at,
        left_at: bc.left_at
      }))
    } catch (e) {
      console.error('[useBillCustomers] Error fetching:', e)
      error.value = e
      customers.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 再読み込み
   */
  async function refresh(billId) {
    await fetchBillCustomers(billId)
  }

  return {
    loading,
    error,
    customers,
    fetchBillCustomers,
    refresh
  }
}
