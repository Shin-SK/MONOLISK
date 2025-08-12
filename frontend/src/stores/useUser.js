// src/stores/useUser.js
import { defineStore } from 'pinia';
import { api } from '@/api'
import { login as authLogin, logout as authLogout } from '@/auth'
/**
 * ログイン状態と /dj-rest-auth/user/ の情報を管理するストア
 */
export const useUser = defineStore('user', {
  // -------------------------------------------------------------------------
  // state
  // -------------------------------------------------------------------------
  state: () => ({
    /** 未取得: null / 未ログイン: {} / ログイン済み: ユーザーオブジェクト */
    info: null,
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
    /**
     * 現在ログイン中のユーザー情報を取得
     * - 401 / 403 は「未ログイン」とみなして空オブジェクトをセット
     */
    async fetch() {
      // 一度取得済みなら再取得しない
      if (this.info !== null && Object.keys(this.info).length) return;

      try {
        const { data } = await api.get('dj-rest-auth/user/');
        this.info = data; // ログイン済み
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401 || status === 403) {
          this.info = {}; // 未ログイン
        } else {
          throw err;      // その他のエラーは上位へ
        }
      }
    },

    /**
     * ログイン
     * @param {string} username
     * @param {string} password
     */
    async login(username, password) {
      await authLogin(username, password);
      this.info = null;                  // キャッシュクリア
      await this.fetch();                // 取得し直し
    },

    /** ログアウト */
    async logout() {
      await authLogout();
      this.clear();
    },

    /** 強制クリア（ストア初期化） */
    clear() {
      this.info = null;
    },
  },
});
