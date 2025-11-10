// src/composables/useTodayShiftPlans.js
import { ref, watchEffect } from 'vue'
import { getShiftPlans } from '@/api'

export function useTodayShiftPlans(storeId = null) {
  const list  = ref([])
  const today = new Date().toISOString().slice(0, 10)   // YYYY-MM-DD

  watchEffect(async () => {
    const params = { date: today, ...(storeId ? { store: storeId } : {}) }
    list.value   = await getShiftPlans(params)
  })

  return { list }
}
