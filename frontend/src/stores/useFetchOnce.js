// src/stores/useFetchOnce.js
import { defineStore } from 'pinia'
import { api } from '@/api'

export const useFetchOnce = defineStore('fetchOnce', {
  state: () => ({
    cache   : {},        // URL → data
    pending : {},        // URL → Promise
  }),

  actions: {
    async get (url, force = false) {
      // 既にキャッシュがあれば即返す
      if (!force && this.cache[url]) return this.cache[url]

      // 取得中ならその Promise を待つ
      if (this.pending[url]) return this.pending[url]

      // 新規リクエスト
      this.pending[url] = api.get(url).then(r => r.data).then(data => {
        this.cache[url] = data
        delete this.pending[url]
        return data
      }).catch(err => {
        delete this.pending[url]
        throw err
      })

      return this.pending[url]
    }
  }
})
