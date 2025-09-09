import { defineStore } from 'pinia'
import { api } from '@/api'
import { login as authLogin, logout as authLogout } from '@/auth'
import { useUser } from '@/stores/useUser'

export const useAuth = defineStore('auth', {
  state: () => ({
    /* Token を Pinia  localStorage に保持しておく */
    token: localStorage.getItem('token') || null,
  }),
  actions: {
    //------------------------------------------------------
    //  ログイン
    //------------------------------------------------------
    async login (username, password) {
      const me = await authLogin(username, password)   // ← auth.js が /me まで返す
      this.token = localStorage.getItem('token') || null
      const userStore = useUser()
      userStore.softClear()
      userStore.me = me                                 // 即時反映
      // 必要に応じて user 情報だけ取得（任意）
      userStore.info = null
      await userStore.fetch()
    },

    //------------------------------------------------------
    //  ログアウト
    //------------------------------------------------------
    async logout () {
      /* サーバ側セッションを無効化（失敗しても無視） */
      try { await authLogout() } catch {}

      /* クライアント側クリーンアップ */
      this.token = null
      localStorage.removeItem('token')
      delete api.defaults.headers.common.Authorization

      useUser().clearAll() 
    },
  },
})
