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

    try {
      // キャッシュを明示的に無効化（pax更新後の同期確認のため）
      const response = await api.get(`/billing/bills/${billId}/customers/`, { cache: false })
      const data = response.data?.results || []

      // 【フェーズ0】API応答の生データをログ出力（DEV環境のみ）
      if (import.meta.env?.DEV) {
        console.log(`[フェーズ0] GET /bills/${billId}/customers/ 応答:`, {
          'results件数': data.length,
          'response.data全体': response.data
        })
      }

      // 整形：display_name がない場合は Guest-XXXXXX を使う（6桁ゼロ埋め）
      customers.value = data.map(bc => {
        const cid = bc.customer_id ?? bc.customer
        const guestName = cid != null ? `Guest-${String(cid).padStart(6, '0')}` : 'Guest'
        return {
          id: bc.id,
          customer_id: cid,
          customer_name: bc.customer_name || bc.display_name || guestName,
          display_name: bc.display_name || bc.customer_name || guestName,
          arrived_at: bc.arrived_at,
          left_at: bc.left_at
        }
      })
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

  /**
   * pax 更新後のリトライ付き再取得。
   * BillCustomer がサーバ側で増殖されるまで短いポーリングで待つ。
   * @param {number} billId
   * @param {number} expectedCount - 期待する最低件数（= newPax）
   * @param {object} [opts]
   * @param {number} [opts.maxRetries=5]
   * @param {number} [opts.interval=250] - リトライ間隔 (ms)
   * @returns {Promise<Array>} 最終的な customers 配列
   */
  async function fetchUntilCount(billId, expectedCount, { maxRetries = 5, interval = 250 } = {}) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      await fetchBillCustomers(billId)
      if (customers.value.length >= expectedCount) break
      if (attempt < maxRetries) {
        if (import.meta.env?.DEV) {
          console.log(`[useBillCustomers] リトライ ${attempt + 1}/${maxRetries}: 期待=${expectedCount}, 実際=${customers.value.length}`)
        }
        await new Promise(r => setTimeout(r, interval))
      }
    }
    return customers.value
  }

  /**
   * BillCustomer を作成
   * @param {number} billId
   * @param {object} payload
   * @returns {Promise<object>} created BillCustomer
   */
  async function createBillCustomer(billId, payload = {}) {
    const response = await api.post(`/billing/bills/${billId}/customers/`, payload)
    return response.data
  }

  /**
   * BillCustomer を更新（PATCH）
   * @param {number} billCustomerId
   * @param {object} payload
   * @returns {Promise<object>} updated BillCustomer
   */
  async function updateBillCustomer(billCustomerId, payload = {}) {
    const response = await api.patch(`/billing/bill-customers/${billCustomerId}/`, payload)
    return response.data
  }

  return {
    loading,
    error,
    customers,
    fetchBillCustomers,
    fetchUntilCount,
    refresh,
    createBillCustomer,
    updateBillCustomer
  }
}
