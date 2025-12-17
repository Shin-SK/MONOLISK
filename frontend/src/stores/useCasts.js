// src/stores/useCasts.js（丸ごと置換）
import { defineStore } from 'pinia'
import { api } from '@/api'
import { listenStoreChanged } from './storeScope'

export const useCasts = defineStore('casts', {
  state: () => ({
    list: [],
    loaded: false,
    error: '',
    _unsub: null,
  }),
  actions: {
    _wireOnce () {
      if (this._unsub) return
      this._unsub = listenStoreChanged(async () => {
        this.reset()
        await this.fetch(true)
      })
    },
    async fetch (storeIdOrForce = false) {
      this._wireOnce()
      // 引数が boolean なら force フラグとして扱う（後方互換）
      const force = typeof storeIdOrForce === 'boolean' ? storeIdOrForce : false
      const storeId = typeof storeIdOrForce === 'number' || typeof storeIdOrForce === 'string' 
        ? storeIdOrForce 
        : null
      
      if (this.loaded && !force) return
      this.error = ''
      try {
        const params = { _ts: Date.now() }
        if (storeId) params.store = storeId
        
        const { data } = await api.get('billing/casts/', {
          cache: false,
          params
        })
        this.list = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
        this.loaded = true
        console.log('[useCasts] fetched:', this.list.length, 'casts for store:', storeId)
      } catch (e) {
        this.error = e?.response?.data?.detail || e.message
        this.list = []
        this.loaded = false
        console.error('[useCasts] fetch failed:', e)
      }
    },
    reset () {
      this.list = []
      this.loaded = false
      this.error = ''
    }
  }
})
