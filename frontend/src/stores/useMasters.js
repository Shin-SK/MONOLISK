// src/stores/useMasters.js
import { defineStore } from 'pinia'
import { useFetchOnce } from './useFetchOnce'

export const useMasters = defineStore('masters', {
  state: () => ({ list: [], loaded: false }),
  actions: {
    async fetch (force = false) {
      if (this.loaded && !force) return
      const once = useFetchOnce()
      // ★ クエリで store を渡さない。ヘッダ X-Store-Id のみで分離
      this.list = await once.get('/billing/item-masters/', force)
      this.loaded = true
    },
    reset () {
      this.list = []
      this.loaded = false
    }
  }
})
