// src/stores/useKDS.js
import { defineStore } from 'pinia'
import { kds } from '@/api'

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

export const useKDS = defineStore('kds', {
  state: () => ({
    // ── station（kitchen / drinker）: NEW/ACK
    tickets: [],
    ticketsCursorId: 0,
    ticketsRunning: false,
    _ticketsCtl: null,     // AbortController

    // ── deshap（READY）
    readyList: [],
    readyIds: new Set(),   // 重複防止用
    readyCursorId: 0,
    readyRunning: false,
    _readyCtl: null,       // AbortController
  }),

  actions: {
    // ========= station: NEW/ACK ロングポーリング =========
    async startLongPollTickets(route) {
      if (this.ticketsRunning) return             // ★多重起動ガード
      this.ticketsRunning = true
      this._ticketsCtl = new AbortController()

      // 初期一覧
      try {
        const base = await kds.listTickets(route)
        this.tickets = Array.isArray(base) ? base : []
        this.ticketsCursorId = this.tickets.reduce((m, x) => Math.max(m, x?.id || 0), 0) || 0
      } catch (e) {
        console.warn('[KDS] listTickets failed:', e?.message || e)
        this.tickets = []
        this.ticketsCursorId = 0
      }

      let backoff = 1000
      while (this.ticketsRunning) {
        try {
          const res = await kds.longPollTickets(route, this.ticketsCursorId, this._ticketsCtl.signal)
          const { tickets = [], cursor = null, retryAfter = 800 } = res || {}

          if (tickets.length) {
            for (const t of tickets) {
              const i = this.tickets.findIndex(x => x.id === t.id)
              if (i >= 0) this.tickets[i] = t
              else this.tickets.unshift(t)
            }
            if (cursor) this.ticketsCursorId = cursor
          } else {
            await sleep(retryAfter)               // ★イベント無し時の待機
          }
          backoff = 1000                          // 正常時はバックオフリセット
        } catch (e) {
          if (this._ticketsCtl?.signal?.aborted) break   // ★停止時は抜ける
          await sleep(backoff)
          backoff = Math.min(backoff * 2, 10000)  // ★指数バックオフ（最大10s）
        }
      }
    },

    stopLongPollTickets() {
      if (this._ticketsCtl) this._ticketsCtl.abort()
      this.ticketsRunning = false
      this._ticketsCtl = null
    },

    ackLocal(id) {
      const i = this.tickets.findIndex(x => x.id === id)
      if (i >= 0) this.tickets[i] = { ...this.tickets[i], state: 'ack' }
    },

    removeLocal(id) {
      const i = this.tickets.findIndex(x => x.id === id)
      if (i >= 0) this.tickets.splice(i, 1)
    },

    // ========= deshap: READY ロングポーリング =========
    async startLongPollReady() {
      if (this.readyRunning) return
      this.readyRunning = true
      this._readyCtl = new AbortController()

      try {
        const base = await kds.readyList()
        this.readyList = Array.isArray(base) ? base : []
        this.readyIds = new Set(this.readyList.map(x => x.id))
        this.readyCursorId = this.readyList.reduce((m, x) => Math.max(m, x?.id || 0), 0) || 0
      } catch (e) {
        console.warn('[KDS] readyList failed:', e?.message || e)
        this.readyList = []
        this.readyIds = new Set()
        this.readyCursorId = 0
      }

      let backoff = 1000
      while (this.readyRunning) {
        try {
          const res = await kds.longPollReady(this.readyCursorId, this._readyCtl.signal)
          const { ready = [], cursor = null, retryAfter = 800 } = res || {}

          if (ready.length) {
            for (const r of ready) {
              if (!this.readyIds.has(r.id)) {
                this.readyList.push(r)
                this.readyIds.add(r.id)
              }
            }
            if (cursor) this.readyCursorId = cursor
          } else {
            await sleep(retryAfter)
          }
          backoff = 1000
        } catch (e) {
          if (this._readyCtl?.signal?.aborted) break
          await sleep(backoff)
          backoff = Math.min(backoff * 2, 10000)
        }
      }
    },

    stopLongPollReady() {
      if (this._readyCtl) this._readyCtl.abort()
      this.readyRunning = false
      this._readyCtl = null
    },

    removeReadyLocal(id) {
      const i = this.readyList.findIndex(x => x.id === id)
      if (i >= 0) this.readyList.splice(i, 1)
      // readyIds は残す（直後の差分で再追加されないように）
    },
  },
})
