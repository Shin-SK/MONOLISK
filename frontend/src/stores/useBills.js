// stores/useBills.js
import { defineStore } from 'pinia'
import * as api from '@/api'

export const useBills = defineStore('bills', {
  state  : () => ({ list: [], current: null }),
  actions: {
    async reload() {                         // ← この名前だけに統一
      if (this.current)
        this.current = await api.fetchBill(this.current.id)
    },
    async loadAll () { this.list = await api.fetchBills() },
    async open (id)  { this.current = await api.fetchBill(id) },
    async addItem (p){ await api.addBillItem(this.current.id, p); await this.reload() },
    async closeCurrent(){ await api.closeBill(this.current.id);     await this.reload() },

    async setInhouseStatus(castIds){
      await api.setInhouseStatus(this.current.id, castIds)
      await this.reload()
    }
  }
})
