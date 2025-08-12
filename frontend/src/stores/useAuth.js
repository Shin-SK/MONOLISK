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
      await authLogin(username, password)                 // 保存とヘッダ設定は auth.js 側でやる
      this.token = localStorage.getItem('token') || null  // 状態だけ同期

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
      try { await authLogout() } catch {}

      /* クライアント側クリーンアップ */
      this.token = null
      localStorage.removeItem('token')
      delete api.defaults.headers.common.Authorization

      useUser().clear()
    },
  },
})
