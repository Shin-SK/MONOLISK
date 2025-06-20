import { defineStore } from 'pinia'
import { login as apiLogin, logout as apiLogout } from '@/api'
import { useUser } from '@/stores/useUser'

export const useAuth = defineStore('auth', {
  actions: {
    async login(username, password) {
      await apiLogin(username, password)   // token 保存
      useUser().clear()
      await useUser().fetch()
    },
    async logout() {
      await apiLogout()                    // ← ここを修正
      useUser().clear()
    }
  }
})