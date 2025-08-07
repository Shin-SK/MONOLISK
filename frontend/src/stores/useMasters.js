// src/stores/useMasters.js
import { defineStore } from 'pinia'
import { useFetchOnce } from './useFetchOnce'
export const useMasters = defineStore('masters', {
  state:() => ({ list:[], loaded:false }),
  actions:{
    async fetch (storeId='', force=false){
      if(this.loaded && !force) return
      const once = useFetchOnce()
      this.list = await once.get(`/billing/item-masters/?store=${storeId}`, force)
      this.loaded = true
    }
  }
})
