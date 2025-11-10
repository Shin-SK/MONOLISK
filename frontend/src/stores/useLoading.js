import { defineStore } from 'pinia'

export const useLoading = defineStore('loading', {
  state : () => ({ count: 0 }),          // ネットワーク数をカウント
  getters: {
    globalLoading: (s) => s.count > 0,
  },
  actions: {
    start() { this.count++ },
    end()   { this.count && this.count-- },
  },
})