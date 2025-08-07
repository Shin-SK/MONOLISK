// src/stores/useCasts.js
import { defineStore } from 'pinia'
import { useFetchOnce } from './useFetchOnce'

export const useCasts = defineStore('casts', {
  state : () => ({
    list   : [],            // 一覧
    byId   : {},            // { 1: {...}, 2: {...} }
    loaded : false,
  }),

  actions : {
    /** 一覧を取得（キャッシュ付） */
    async fetch (force = false) {
      if (this.loaded && !force) return
      const once = useFetchOnce()
      const raw  = await once.get('/billing/casts/', force)
	  this.list  = raw.results ?? raw
      this.byId = Object.fromEntries(this.list.map(c => [c.id, c]))
      this.loaded = true
    },

    /** 個別取得（キャッシュに無ければ API へ） */
    async get (id, force = false) {
      if (!force && this.byId[id]) return this.byId[id]
      const once = useFetchOnce()
      const cast = await once.get(`/billing/casts/${id}/`, force)
      this.byId[id] = cast
      return cast
    },
  },
})
