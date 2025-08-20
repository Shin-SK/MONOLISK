// stores/useBills.js
import { defineStore } from 'pinia'
import { api, fetchBill, addBillItem, closeBill, setInhouseStatus } from '@/api'
import { useLoading } from '@/stores/useLoading'
import { useFetchOnce } from './useFetchOnce'

export const useBills = defineStore('bills', {
  state : () => ({
    list     : [],     // ← 参照を不変に保つ（空にしない）
    current  : null,
    _inflight: false,
    _timer   : null,
    lastUpdated: null,
    _pollCount : 0,
  }),

  actions: {
    async loadAll (force = false) { await this.fetch(force) },

    // 一覧の取得：配列“丸ごと代入”をやめ、差分パッチに変更
    async fetch (force=false) {
      if (this._inflight) return
      this._inflight = true
      try {
        const fetchOnce = useFetchOnce()
        const data = await fetchOnce.get('/billing/bills/', force) // Array
        this._patchListInPlace(data)
      } finally {
        this._inflight = false
      }
    },

    // 背景更新（ローダーを出さない版）
    async fetchBg () {
      if (this._inflight) return
      this._inflight = true
      try {
        const { data } = await api.get('billing/bills/', {
          meta: { silent: true }   // ← ヘッダではなく meta を使う
        })
        this._patchListInPlace(data)
        this._pollCount
        this.lastUpdated = new Date().toISOString()
        console.debug('[poll]', this._pollCount, this.lastUpdated, { count: this.list.length })
      } finally {
        this._inflight = false
      }
    },

    // 参照は維持したまま中身だけ更新（upsert + prune）
    _patchListInPlace(newList) {
      const byId = new Map(this.list.map(b => [b.id, b]))
      const seen = new Set()

      for (const nb of newList) {
        const ex = byId.get(nb.id)
        if (ex) {
          Object.assign(ex, nb)     // ← 既存オブジェクトを上書き
        } else {
          this.list.push(nb)        // ← 新規だけ追加
        }
        seen.add(nb.id)
      }
      for (let i = this.list.length - 1; i >= 0; i--) {
        if (!seen.has(this.list[i].id)) this.list.splice(i, 1) // ← 消えたものだけ削除
      }
    },

    // ポーリング制御（画面側から呼ぶ）
    startPolling(intervalMs = 60_000) {
      if (this._timer) return
      // 即1回叩いて可視化
      this.fetchBg()
      this._timer = setInterval(() => this.fetchBg(), intervalMs)
    },
    stopPolling() {
      if (!this._timer) return
      clearInterval(this._timer)
      this._timer = null
    },

    /* ---------- 個別・操作系はそのまま ---------- */
    async open (id) {
      const loading = useLoading()
      loading.start()
      try {
        this.current = await fetchBill(id)
      } finally { loading.end() }
    },
    async reload () { this.current && await this.open(this.current.id) },

    async addItem (payload) {
      const loading = useLoading()
      loading.start()
      try {
        await addBillItem(this.current.id, payload)
        await this.reload()
      } finally { loading.end() }
    },
    async closeCurrent () {
      const loading = useLoading()
      loading.start()
      try {
        await closeBill(this.current.id)
        await this.reload()
      } finally { loading.end() }
    },
    async setInhouseStatus (castIds) {
      const loading = useLoading()
      loading.start()
      try {
        await setInhouseStatus(this.current.id, castIds)
        await this.reload()
      } finally { loading.end() }
    },
  },
})
