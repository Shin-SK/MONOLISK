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
    async fetch (force = false) {
      this._wireOnce()
      if (this.loaded && !force) return
      this.error = ''
      try {
        // ★ キャッシュ無効 + タイムスタンプで確実に最新化
        const { data } = await api.get('billing/casts/', {
          cache: false,
          params: { _ts: Date.now() }
        })
        this.list = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
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
