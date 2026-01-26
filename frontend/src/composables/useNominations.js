/* src/composables/useNominations.js */
import { ref } from 'vue'
import { api } from '@/api'

/**
 * 本指名設定（BillCustomerNomination）を管理
 * 
 * 返すもの：
 * {
 *   loading: ref(false),
 *   error: ref(null),
 *   nominations: ref([]),
 *   fetchNominations: async (billId) => void,
 *   setNominations: async (billId, customerId, castIds) => void,
 *   removeNomination: async (billId, nominationId) => void
 * }
 */
export function useNominations() {
  const loading = ref(false)
  const error = ref(null)
  const nominations = ref([])

  /**
   * billId の全 nominations を取得
   */
  async function fetchNominations(billId) {
    loading.value = true
    error.value = null
    nominations.value = []

    try {
      const response = await api.get(`/billing/bills/${billId}/nominations/`)
      nominations.value = response.data?.results || []
    } catch (e) {
      console.error('[useNominations.fetchNominations]', e)
      error.value = e
      nominations.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 顧客の本指名キャスト一覧を設定（置換）
   * backend側が既存削除→新規作成の差分処理をしてくれる
   */
  async function setNominations(billId, customerId, castIds) {
    loading.value = true
    error.value = null

    try {
      const response = await api.post(`/billing/bills/${billId}/nominations/`, {
        customer_id: customerId,
        cast_ids: castIds
      })
      
      // 成功後に全nominations を再取得
      await fetchNominations(billId)
    } catch (e) {
      console.error('[useNominations.setNominations]', e)
      error.value = e
    } finally {
      loading.value = false
    }
  }

  /**
   * 個別の Nomination を削除
   * DELETE /api/billing/bills/{billId}/nominations/{nominationId}/
   */
  async function removeNomination(billId, nominationId) {
    loading.value = true
    error.value = null

    try {
      // backend が DELETE /bills/{id}/nominations/{nomination_id}/ に対応していない場合は
      // bill-customer-nominations/{id} で削除する代替方法を検討
      // 現在は nominations/{id} ルートで削除を試みる
      await api.delete(`/billing/bills/${billId}/nominations/${nominationId}/`)
      
      // 成功後に再取得
      await fetchNominations(billId)
    } catch (e) {
      console.error('[useNominations.removeNomination]', e)
      error.value = e
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    nominations,
    fetchNominations,
    setNominations,
    removeNomination
  }
}
