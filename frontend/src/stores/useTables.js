// src/stores/useTables.js
import { defineStore } from 'pinia'
import { useFetchOnce } from './useFetchOnce'
export const useTables = defineStore('tables', {
  state:() => ({ list:[], loaded:false }),
  actions:{
    async fetch (storeId='', force=false){
      if(this.loaded && !force) return
      const once = useFetchOnce()
      this.list = await once.get(`/billing/tables/?store=${storeId}`, force)
      this.loaded = true
    }
  }
})
