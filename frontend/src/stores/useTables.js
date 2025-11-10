// src/stores/useTables.js
import { defineStore } from 'pinia'
import { api } from '@/api'

export const useTables = defineStore('tables', {
  state: () => ({ list: [], loaded: false, error: '' }),
  actions: {
    async fetch (force = false) {
      if (this.loaded && !force) return
      this.error = ''
      try {
        const { data } = await api.get('billing/tables/', { cache: true })
        this.list = Array.isArray(data) ? data : (data?.results ?? [])
        this.loaded = true
      } catch (e) {
        this.error = e?.response?.data?.detail || e.message
        this.list = []
        this.loaded = false
      }
    },
    reset () {
      this.list = []
      this.loaded = false
      this.error = ''
    }
  }
})
