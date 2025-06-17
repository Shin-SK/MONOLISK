// src/stores/useAuth.js
import { defineStore } from 'pinia';
import { api } from '@/api';
import { useUser } from '@/stores/useUser';

export const useAuth = defineStore('auth', {
  actions : {
    async login (username, password) {
      // dj-rest-auth は Cookie を返すので token 管理は不要
      await api.post('dj-rest-auth/login/', { username, password });
      useUser().clear();      // 状態をリセットして…
      await useUser().fetch(); // …最新ユーザ情報を取得
    },
    async logout () {
      await api.post('dj-rest-auth/logout/');
      useUser().clear();
    }
  }
});
