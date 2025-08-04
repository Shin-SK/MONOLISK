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
export function clearAuth  ()      { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(STORE_KEY) }

/* ------------------------------------------------ *
 *  認証 API
 * ------------------------------------------------ */

/** ログイン
 *  - 成功時: token と store_id を保存
 *  - 失敗時: throw で呼び出し側に通知（api インターセプタが alert 済み）
 */
export async function login(username, password) {
  clearAuth()                                          // 念のため全クリア
  const { data } = await api.post('dj-rest-auth/login/', { username, password })
  localStorage.setItem(TOKEN_KEY, data.key)
  if (data.store_id) setStoreId(data.store_id)
}

/** ログアウト（常に成功扱い） */
export async function logout() {
  try { await api.post('dj-rest-auth/logout/') } catch (_) {}
  clearAuth()
}
