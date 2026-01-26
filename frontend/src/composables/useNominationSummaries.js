/* src/composables/useNominationSummaries.js */
import { ref } from 'vue'
import { api } from '@/api'

export function useNominationSummaries() {
  const loading = ref(false)
  const error = ref(null)
  const results = ref([])

  /**
   * 本指名サマリーを取得
   * @param {number} billId
   * @param {Date} now - オプション：未来時刻の計算用
   */
  async function fetchNominationSummaries(billId, now = null) {
    loading.value = true
    error.value = null
    results.value = []

    try {
      const params = {}
      if (now) {
        params.now = now.toISOString()
      }

      const response = await api.get(`/billing/bills/${billId}/nomination-summaries/`, { params })
      results.value = response.data?.results || []
    } catch (e) {
      console.error('[useNominationSummaries] Error fetching:', e)
      error.value = e
      results.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 再読み込み
   */
  async function refresh(billId, now = null) {
    await fetchNominationSummaries(billId, now)
  }

  return {
    loading,
    error,
    results,
    fetchNominationSummaries,
    refresh
  }
}
