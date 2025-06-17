// src/stores/useUser.js
import { defineStore } from 'pinia';
import { api } from '@/api';

export const useUser = defineStore('user', {
  state : () => ({
    info: null          // dj-rest-auth/user/ 全体を保持
  }),

  getters : {
    avatar : s => s.info?.avatar_url ?? '/static/img/user-default.png',
    name   : s => s.info?.display_name || s.info?.username || '',
    isDriver : s => s.info?.groups?.includes('DRIVER') ?? false,
    isCast   : s => s.info?.groups?.includes('CAST')   ?? false,   // 既存
    isStaff  : s => !s.isDriver && !s.isCast,                      // STAFF 判定
    fullName : s => s.info?.display_name || s.info?.username || '',
    isStaff () { return !this.isDriver && !this.isCast }
  },

  actions : {
    async fetch () {
      if (this.info !== null) return;           // 既に取得済み
      try {
        const { data } = await api.get('dj-rest-auth/user/');
        this.info = data;                       // ログイン済み
      } catch (err) {
        if (err?.response?.status === 403) this.info = {};   // 未ログイン
        else throw err;
      }
    },
    clear () { this.info = null; }
  }
});
