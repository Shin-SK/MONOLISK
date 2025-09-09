// src/auth.js  ← これで全置換
import { api } from './api'

const TOKEN_KEY = 'token'
const STORE_KEY = 'store_id'

export function getToken()      { return localStorage.getItem(TOKEN_KEY) }
export function getStoreId()    { return localStorage.getItem(STORE_KEY) }
export function setStoreId(id)  {
	localStorage.setItem(STORE_KEY, String(id))
	console.log('[auth] setStoreId:', id, '-> now:', localStorage.getItem('store_id'))
}
export function clearAuth() {
	localStorage.removeItem(TOKEN_KEY)
	localStorage.removeItem(STORE_KEY)
	delete api.defaults.headers.common.Authorization
	console.log('[auth] clearAuth()')
}

/**
 * ログイン手順（堅牢版）
 * 1) token保存
 * 2) /dj-rest-auth/user の legacy store_id を先に保存（あれば）
 * 3) /api/me（非依存）で“現在店舗”を決定 → あれば上書き
 * 4) 決定した store_id で /api/me を再取得（role/caps を現店舗で）
 */
export async function login(username, password) {
	clearAuth()

	// 1) 認証
	const { data } = await api.post('dj-rest-auth/login/', { username, password })
	const token = data?.key
	if (!token) throw new Error('login failed')
	localStorage.setItem(TOKEN_KEY, token)
	api.defaults.headers.common.Authorization = `Token ${token}`
	console.log('[auth] login ok, token saved')

	// ★ サーバのレスポンスに store_id があれば即保存（最優先）
	if (data?.store_id != null) {
		setStoreId(data.store_id)
		console.log('[auth] set store_id from login:', data.store_id, '-> now:', localStorage.getItem('store_id'))
	}

	// 2) legacy: /dj-rest-auth/user
	try {
		const u = (await api.get('dj-rest-auth/user/')).data
		if (u?.store_id != null && getStoreId() == null) {
			setStoreId(u.store_id)
			console.log('[auth] set store_id from /dj-rest-auth/user:', u.store_id)
		}
	} catch (e) {
		console.warn('[auth] fetch user failed (ok to ignore):', e?.message)
	}

	// 3) /api/me（ヘッダ不要）
	let me = (await api.get('me/')).data
	const decided =
		me?.current_store_id ??
		me?.primary_store_id ??
		(Array.isArray(me?.stores) && me.stores.length ? me.stores[0] : null)

	if (decided != null) {
		setStoreId(decided)
		console.log('[auth] set store_id from /me:', decided)
	} else if (!getStoreId()) {
		// 最後の保険：所属店舗一覧の先頭
		try {
			const list = (await api.get('billing/stores/my/')).data
			if (Array.isArray(list) && list.length) {
				setStoreId(list[0].id)
				console.log('[auth] set store_id from /stores/my:', list[0].id)
			}
		} catch (e) {
			console.warn('[auth] stores/my failed:', e?.message)
		}
	}

	// 4) 決定した store_id で /api/me を再取得（現店舗のrole/capsを即反映）
	const sid = getStoreId()
	console.log('[auth] sid before /me re-fetch:', sid)
	if (!sid) throw new Error('店舗所属が未設定です。管理者に店舗割当をしてください。')

	me = (await api.get('me/', { headers: { 'X-Store-Id': String(sid) } })).data
	console.log('[auth] /me re-fetch current_store_id:', me?.current_store_id)

	return me
}

export async function logout() {
	try { await api.post('dj-rest-auth/logout/') } catch {}
	clearAuth()
}
