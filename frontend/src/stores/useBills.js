// stores/useBills.js
import { defineStore } from 'pinia'
import { fetchBills, fetchBill, addBillItem, closeBill,
         setInhouseStatus } from '@/api'
import { useLoading } from '@/stores/useLoading'
console.log('[useBills] store loaded')
export const useBills = defineStore('bills', {
  state : () => ({ list: [], current: null }),

  actions: {
    /* 一覧 ---------------------------------------------------- */
    
    async loadAll () {
      console.log('[useBills] loadAll start')
      this.list = await fetchBills()      // ← インターセプタが start/end する
       console.log('[useBills] loadAll end')
    },

    /* 1 伝票 -------------------------------------------------- */
    async open (id) {
      const loading = useLoading()
      loading.start()
      try {
        this.current = await fetchBill(id)
      } finally {
        loading.end()
      }
    },
    async reload () { this.current && await this.open(this.current.id) },

    /* 明細追加・クローズなど ---------------------------------- */
    async addItem (payload) {
      const loading = useLoading()
      loading.start()
      try {
        await addBillItem(this.current.id, payload)
        await this.reload()
      } finally {
        loading.end()
      }
    },
    async closeCurrent () {
      const loading = useLoading()
      loading.start()
      try {
        await closeBill(this.current.id)
        await this.reload()
      } finally {
        loading.end()
      }
    },
    async setInhouseStatus (castIds) {
      const loading = useLoading()
      loading.start()
      try {
        await setInhouseStatus(this.current.id, castIds)
        await this.reload()
      } finally {
        loading.end()
      }
    },
  },
})
