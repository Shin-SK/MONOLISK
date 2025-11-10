// src/stores/useCustomers.ts / .js
import { defineStore } from 'pinia'
import { api } from '@/api'

export const useCustomers = defineStore('customers', {
  state: () => ({
    /** id → customerObj のキャッシュ */
    cache: new Map(),                          
  }),

  actions: {
    /** 検索 */
    async search(q = '', { silent = false } = {}) {
      if (!q.trim()) return []

      const { data } = await api.get('billing/customers/', { params: { q } })
      const list = data.results ?? data        // ページネーション両対応

      if (!silent) {
        list.forEach(c => this.cache.set(c.id, c))
      }
      return list
    },
    /** ID 1 件または検索 params を受け取り、customer オブジェクトを返す */
    async fetchOne(idOrParams) {
      if (idOrParams == null) return null

      // ── params オブジェクト → 一覧 API で 1 件目を返す
      if (typeof idOrParams === 'object') {
        const { data } = await api.get('billing/customers/', { params: idOrParams })
        const list = data.results ?? data
        const c = Array.isArray(list) ? list[0] ?? null : null
        if (c) this.cache.set(c.id, c)
        return c
      }

      // ── 純粋な ID → /billing/customers/:id/
      const { data } = await api.get(`billing/customers/${idOrParams}/`)
      this.cache.set(data.id, data)
      return data
    },

    /** 表示用ラベルを即返す（足りなければ裏で fetchOne しておく） */
    getLabel(id) {
      const c = this.cache.get(id)
      if (!c) this.fetchOne(id)             // 非同期 fetch だけ仕込む
      return c?.alias?.trim() || c?.full_name || `#${id}`
    },

    /** 新規／更新保存 */
    async save(payload) {
      const { data } = payload.id
        ? await api.patch(`billing/customers/${payload.id}/`, payload)
        : await api.post('billing/customers/', payload)
      this.cache.set(data.id, data)
      return data
    },
  },
})
