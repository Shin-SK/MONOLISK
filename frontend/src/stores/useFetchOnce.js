// src/stores/useFetchOnce.js
import { defineStore } from 'pinia'
import { api } from '@/api'
import { listenStoreChanged, getPinnedStoreId } from './storeScope'

export const useFetchOnce = defineStore('fetchOnce', {
  state: () => ({
    cache   : {},   // key → data
    pending : {},   // key → Promise
    _unsub  : null,
  }),

  actions: {
    _key (url) {
      const sid = getPinnedStoreId() || 'none'
      // 同じURLでも store が違えば別キャッシュにする
      return `[sid:${sid}] ${String(url)}`
    },

    _wireOnce () {
      if (this._unsub) return
      this._unsub = listenStoreChanged(() => {
        // 店舗切替でキャッシュ/pendingを全て捨てる
        this.cache = {}
        this.pending = {}
      })
    },

    async get (url, force = false) {
      this._wireOnce()
      const key = this._key(url)

      if (!force && this.cache[key]) return this.cache[key]
      if (this.pending[key]) return this.pending[key]

      this.pending[key] = api.get(url).then(r => r.data).then(data => {
        this.cache[key] = data
        delete this.pending[key]
        return data
      }).catch(err => {
        delete this.pending[key]
        throw err
      })

      return this.pending[key]
    }
  }
})
