// src/auth.js
import { api } from './api'          // 既存 axios インスタンスを再利用

/* ------------------------------------------------ *
 *  ローカルストレージ key を 1 ヶ所で定義
 * ------------------------------------------------ */
const TOKEN_KEY  = 'token'
const STORE_KEY  = 'store_id'

export function getToken   ()      { return localStorage.getItem(TOKEN_KEY)  }
export function getStoreId ()      { return localStorage.getItem(STORE_KEY)  }
export function setStoreId (id)    { localStorage.setItem(STORE_KEY, String(id)) }
export function clearAuth  () {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(STORE_KEY)
  delete api.defaults.headers.common.Authorization   // ← 追加
}

/* ------------------------------------------------ *
 *  認証 API
 * ------------------------------------------------ */

/** ログイン
 *  - 成功時: token と store_id を保存
 *  - 失敗時: throw で呼び出し側に通知（api インターセプタが alert 済み）
 */
export async function login(username, password) {
  clearAuth()
  const { data } = await api.post('dj-rest-auth/login/', { username, password })
  localStorage.setItem(TOKEN_KEY, data.key)
  api.defaults.headers.common.Authorization = `Token ${data.key}`  // ← これ追加
  if (data.store_id) {
    setStoreId(data.store_id)
  } else {
    try {
      const meStore = await api.get('billing/stores/me/')
      if (meStore?.data?.id) setStoreId(meStore.data.id)
    } catch (_) { /* 取れなかったらスキップ（後続画面で選ばせる想定でもOK）*/ }
  }
}


/** ログアウト（常に成功扱い） */
export async function logout() {
  try { await api.post('dj-rest-auth/logout/') } catch (_) {}
  clearAuth()
}
