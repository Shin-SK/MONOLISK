// stores/useBills.js
import { defineStore } from 'pinia'
import { api, fetchBill, addBillItem, closeBill, setInhouseStatus } from '@/api'
import { useLoading } from '@/stores/useLoading'
import { useFetchOnce } from './useFetchOnce'

export const useBills = defineStore('bills', {
  state : () => ({
    list       : [],     // 参照は保つ
    current    : null,
    _inflight  : false,
    _timer     : null,
    lastUpdated: null,
    _pollCount : 0,
  }),

  actions: {
    async loadAll (force = false) {
      await this.fetch(force)
    },

    // 一覧の取得：force=true は “本当に”キャッシュ無視で取り直し
    async fetch (force=false) {
      if (this._inflight) return
      this._inflight = true
      try {
        let data
        if (force) {
          // ★ キャッシュ無効 + ブレーカー
          const { data:raw } = await api.get('billing/bills/', {
            params: { _ts: Date.now() },
            cache : false,
          })
          data = this._normalizeList(raw)
        } else {
          const fetchOnce = useFetchOnce()
          const raw = await fetchOnce.get('/billing/bills/', force) // Array or {results}
          data = this._normalizeList(raw)
        }
        this._patchListInPlace(data)
        this.lastUpdated = new Date().toISOString()
      } finally {
        this._inflight = false
      }
    },

    // 背景更新（ローダーなし）
    async fetchBg () {
      if (this._inflight) return
      this._inflight = true
      try {
        const { data:raw } = await api.get('billing/bills/', {
          params: { _ts: Date.now() },
          cache : false,
          meta  : { silent: true },   // ← ローディング非表示
        })
        const data = this._normalizeList(raw)
        this._patchListInPlace(data)
        this._pollCount += 1
        this.lastUpdated = new Date().toISOString()
        if (import.meta.env.DEV) {
          // console.debug('[poll]', this._pollCount, this.lastUpdated, { count: this.list.length })
        }
      } finally {
        this._inflight = false
      }
    },

    // 参照は維持したまま中身だけ更新（upsert + prune）
    _patchListInPlace(newList) {
      const byId = new Map(this.list.map(b => [b.id, b]))
      const seen = new Set()

      for (const nb of newList) {
        if (!nb || nb.id == null) continue
        const ex = byId.get(nb.id)
        if (ex) {
          // ★ ゴースト対策：旧キーを残したままマージすると、サーバ応答に
          //   含まれないフィールド（編集で消えた items / customers / 派生値 等）が
          //   居残ってしまうため、新レスポンスのキーで完全に置き換える。
          const merged = { ...nb }
          // 楽観的に closed_at を付けている場合、サーバ未反映のレスポンスで消さない
          if (ex.closed_at && !nb.closed_at) {
            merged.closed_at = ex.closed_at
            // ゴースト防止：stays も退席扱いを維持
            merged.stays = (merged.stays || []).map(s => s.left_at ? s : ({ ...s, left_at: ex.closed_at }))
            // settled_total が既にローカルにあれば維持
            if (ex.settled_total && !nb.settled_total) merged.settled_total = ex.settled_total
          }
          // _syncState, _dirty はサーバー応答で上書きしない（txQueue が管理する）
          if (ex._syncState) merged._syncState = ex._syncState
          if (ex._dirty) merged._dirty = ex._dirty
          // dirty フィールドはローカル値を保護
          const dirty = ex._dirty
          if (dirty && dirty.size > 0) {
            for (const f of dirty) {
              if (f in ex) merged[f] = ex[f]
            }
          }
          // 既存オブジェクトの参照は維持しつつ、中身は新レスポンスで総入れ替え
          for (const k of Object.keys(ex)) {
            if (k.startsWith('_')) continue // _dirty, _syncState は保護
            if (!(k in merged)) delete ex[k]
          }
          Object.assign(ex, merged)
        } else {
          this.list.push(nb)        // 新規だけ追加
        }
        seen.add(nb.id)
      }
      // ★ 楽観的tempID（負数）はポーリング削除対象から除外
      for (let i = this.list.length - 1; i >= 0; i--) {
        const bid = this.list[i].id
        if (!seen.has(bid) && bid > 0) {
          this.list.splice(i, 1) // サーバに無い正IDのみ削除
        }
      }
    },

    // DRFの {results:[]} / 素配列 の両対応
    _normalizeList(raw) {
      if (Array.isArray(raw?.results)) return raw.results
      if (Array.isArray(raw)) return raw
      return []
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

    /* ---------- 個別・操作系 ---------- */
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
        const billId = this.current.id
        await closeBill(billId)
        // ★ 即時ローカル更新：ポーリングを待たずにclosed_atを設定しゴースト防止
        const localBill = this.list.find(b => b.id === billId)
        if (localBill) {
          localBill.closed_at = new Date().toISOString()
        }
        // current もクリア（編集中状態の解除）
        this.current = null
        // サーバ最新を再取得して全体整合性確保
        await this.fetch(true)
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