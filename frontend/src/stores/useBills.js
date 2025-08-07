// stores/useBills.js
import { defineStore } from 'pinia'
import { fetchBill, addBillItem, closeBill, setInhouseStatus } from '@/api'
import { useLoading } from '@/stores/useLoading'
import { useFetchOnce } from './useFetchOnce'

export const useBills = defineStore('bills', {
  state : () => ({
    list   : [],   // 一覧
    current: null, // 個別
  }),

  actions: {

    async loadAll (force = false) { await this.fetch(force) },

    /* 一覧 -------------------------------------------------- */
    async fetch (force=false) {
      const fetchOnce = useFetchOnce()
      this.list = await fetchOnce.get('/billing/bills/', force)
    },

    /* 1 伝票 ------------------------------------------------ */
    async open (id) {
      const loading = useLoading()
      loading.start()
      try {
        this.current = await fetchBill(id)
      } finally { loading.end() }
    },
    async reload () { this.current && await this.open(this.current.id) },

    /* 明細追加など ---------------------------------------- */
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
