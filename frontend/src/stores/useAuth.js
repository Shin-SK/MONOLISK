import { defineStore } from 'pinia'
import { login as apiLogin, logout as apiLogout, api } from '@/api'
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
      /* apiLogin は { token } を返す想定 */
      const token = await apiLogin(username, password)

      /* クライアント側に保持 */
      this.token = token
      localStorage.setItem('token', token)
      api.defaults.headers.common.Authorization = `Token ${token}`

      /* ユーザー情報を改めてロード */
      const userStore = useUser()
      userStore.clear()
      await userStore.fetch()
    },

    //------------------------------------------------------
    //  ログアウト
    //------------------------------------------------------
    async logout () {
      /* サーバ側セッションを無効化（失敗しても無視） */
      try { await apiLogout() } catch { /* already gone → ignore */ }

      /* クライアント側クリーンアップ */
      this.token = null
      localStorage.removeItem('token')
      delete api.defaults.headers.common.Authorization

      useUser().clear()
    },
  },
})
