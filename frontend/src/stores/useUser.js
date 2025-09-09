// src/stores/useUser.js
import { reactive } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api'
import { login as authLogin, logout as authLogout } from '@/auth'

// 「can()」互換（claimsをグローバルから参照している既存コード向け）
const shared = reactive({ me: null })
export const can = (cap) => !!shared.me?.claims?.includes(cap)

function ensurePinnedInMembership(me){
	const pinned = localStorage.getItem('store_id')
	if (!pinned) return
	const sid = Number(pinned)
	const stores = Array.isArray(me?.stores) ? me.stores : []
	if (!stores.includes(sid)) {
		const fallback = me?.primary_store_id ?? me?.current_store_id ?? null
		if (fallback) {
			localStorage.setItem('store_id', String(fallback))
			console.warn('[user] pinned store_id was not in memberships. fallback ->', fallback)
		} else {
			localStorage.removeItem('store_id')
		}
	}
}


/**
 * ユーザー状態ストア
 * ルール：
 *  - /api/me には store_id を付けない（サーバに任せる）
 *  - fetchMe() 後、localStorage.store_id が未設定のときだけ
 *    me.current_store_id（→ なければ primary_store_id）を保存する
 *  - すでに store_id がある場合は **上書きしない**（＝伝票等で決まった店舗を優先）
 */
export const useUser = defineStore('user', {
  // -------------------------------------------------------------------------
  // state
  // -------------------------------------------------------------------------
  state: () => ({
    /** 未取得: null / 未ログイン: {} / ログイン済み: ユーザーオブジェクト */
    info: null,     // dj-rest-auth/user/ 用（互換）
    me:   null,     // /api/me 用（現在運用の基準）
  }),

  // -------------------------------------------------------------------------
  // getters
  // -------------------------------------------------------------------------
  getters: {
    avatar:   (s) => s.info?.avatar_url || '/img/user-default.png',
    name:     (s) => s.info?.display_name || s.info?.username || '',
    isDriver: (s) => s.info?.groups?.includes('DRIVER') ?? false,
    isCast:   (s) => s.info?.groups?.includes('CAST')   ?? false,
    isStaff() { return !this.isDriver && !this.isCast },
    fullName() { return this.name },
  },

  // -------------------------------------------------------------------------
  // actions
  // -------------------------------------------------------------------------
  actions: {
    /** dj-rest-auth/user/（互換） */
    async fetch() {
      if (this.info !== null && Object.keys(this.info).length) return
      try {
        const { data } = await api.get('dj-rest-auth/user/')
        this.info = data
      } catch (err) {
        const status = err?.response?.status
        if (status === 401 || status === 403) {
          this.info = {}
        } else {
          throw err
        }
      }
    },

    /**
     * /api/me を取得
     * - ここでは localStorage.store_id を **上書きしない**
     *   （既に設定されていれば＝伝票等で決まった店舗を優先）
     * - 未設定時のみ current_store_id → primary_store_id の順で初期化
     */
    async fetchMe() {
      const { data } = await api.get('me/')   // ← /api/me には store_id を付けないこと（api.js で SKIP_STORE に入れる）
      this.me = data
      shared.me = data

      const hasPinned = !!localStorage.getItem('store_id')
      if (!hasPinned) {
        const sid = data?.current_store_id || data?.primary_store_id || null
        if (sid) localStorage.setItem('store_id', String(sid))
      }
      ensurePinnedInMembership(data)
      return data
    },

    /** 明示的にアクティブ店舗を切り替える（将来の店舗スイッチ/伝票確定時に使用） */
    setActiveStore(storeId) {
      if (storeId == null) {
        localStorage.removeItem('store_id')
      } else {
        localStorage.setItem('store_id', String(storeId))
      }
    },

    /** ログイン */
    async login(username, password) {
      await authLogin(username, password)
      this.info = null
      await this.fetch()
      // /api/me も必要ならここで呼ぶ
      await this.fetchMe()
    },

    /** ログアウト */
    async logout() {
      await authLogout()
      this.clear()
    },

    /** 強制クリア */
    clear() {
      this.info = null
      this.me   = null
      shared.me = null
      // 店舗ピン止めも解除（ログアウト時は毎回初期化）
      localStorage.removeItem('store_id')
    },
  },
})

