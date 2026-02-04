import { ref, computed } from 'vue'
import api from '@/api.js'

/* ヘルパー：重複除去 */
function dedupe(arr) {
  return Array.isArray(arr) ? Array.from(new Set(arr)) : []
}

export function useBills() {
  const bills = ref([])
  const loading = ref(false)
  const error = ref(null)

  const createBill = async (payload) => {
    try {
      loading.value = true
      error.value = null
      
      // Extract tableIds from payload
      const { tableIds, ...rest } = payload
      
      // Create request body with table_ids (never include legacy table or table_id)
      const body = {
        ...rest,
      }
      if (Array.isArray(tableIds)) {
        body.table_ids = dedupe(tableIds)  // 重複除去
      }
      
      const response = await api.post('/billing/bills/', body)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateBill = async (billId, payload) => {
    try {
      loading.value = true
      error.value = null
      
      // Extract tableIds from payload
      const { tableIds, ...rest } = payload
      
      // Create request body with table_ids (never include legacy table or table_id)
      const body = {
        ...rest,
      }
      if (Array.isArray(tableIds)) {
        body.table_ids = dedupe(tableIds)  // 重複除去
      }
      
      const response = await api.patch(`/billing/bills/${billId}/`, body)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchBills = async (params = {}) => {
    try {
      loading.value = true
      error.value = null
      const response = await api.get('/billing/bills/', { params })
      bills.value = response.data.results || response.data
      return bills.value
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteBill = async (billId) => {
    try {
      loading.value = true
      error.value = null
      await api.delete(`/billing/bills/${billId}/`)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    bills,
    loading,
    error,
    createBill,
    updateBill,
    fetchBills,
    deleteBill
  }
}
