// src/api/interceptors.js
import { useLoading } from '@/stores/useLoading'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

const TOKEN_KEY = 'token'
const STORE_KEY = 'store_id'
const getToken   = () => localStorage.getItem(TOKEN_KEY)
const getStoreId = () => localStorage.getItem(STORE_KEY)

const DEFAULT_SKIP_AUTH = [
  'dj-rest-auth/login/',
  'dj-rest-auth/registration/',
  'auth/registration/',        // ← 追加（/api/auth/registration/配下）
  'dj-rest-auth/password/reset/',
]

const DEFAULT_SKIP_STORE = [
	'me/',               // /api/me はStore非依存
]

function pathFrom(cfg, baseURL='') {
	const urlStr = cfg.url || ''

	// 絶対URLならそのまま
	if (/^https?:\/\//i.test(urlStr)) {
		try { return new URL(urlStr).pathname.replace(/^\/+|\/+$/g, '') } catch {}
	}

	// baseURL が絶対URLなら利用
	if (baseURL && /^https?:\/\//i.test(baseURL)) {
		try { return new URL(urlStr, baseURL).pathname.replace(/^\/+|\/+$/g, '') } catch {}
	}

	// 最後の保険：location.origin で解決（devでも動く）
	try {
		return new URL(urlStr, window.location.origin).pathname.replace(/^\/+|\/+$/g, '')
	} catch {
		// それでも無理なら先頭スラッシュを落として返す
		return String(urlStr).replace(/^\/+/, '')
	}
}

function isApiMePath(p){
  const s = (p || '').replace(/^\/+|\/+$/g,'')  // 'api/me' or 'me'
  return s === 'api/me' || s === 'me'
}

export function wireInterceptors(api, {
  skipAuth  = DEFAULT_SKIP_AUTH,
  // ← skipStoreは使わず、/api/me を厳密関数で判定する
  skipStore = DEFAULT_SKIP_STORE, // 残してOKだが使わない
} = {}) {
  api.interceptors.request.use(cfg => {
    const loading = useLoading()
    const isKDS   = /\/billing\/kds\//.test(cfg.url || '')
    const silent  = isKDS || cfg.headers?.['X-Silent'] === '1' || cfg.meta?.silent
    if (!silent) { loading.start(); NProgress.start() }

    if (cfg.data instanceof FormData) delete cfg.headers['Content-Type']

    if (!skipAuth.some(p => (cfg.url || '').includes(p))) {
      const t = getToken()
      if (t) cfg.headers.Authorization = `Token ${t}`
    }

    // ★ ここを厳密化：/api/me だけ除外
    const p = pathFrom(cfg, api.defaults.baseURL)
    if (!isApiMePath(p)) {
      const sid = getStoreId()
      if (sid) cfg.headers['X-Store-Id'] = String(sid)
      else console.warn('[api] X-Store-Id missing for Store-Locked API:', p)
    }

    // ★ 残骸クリーニング（params と url 文字列の両方）
    if (cfg.params) { delete cfg.params.store_id; delete cfg.params.store }
    if (typeof cfg.url === 'string' && cfg.url.includes('?')) {
      const [path, query] = cfg.url.split('?')
      const sp = new URLSearchParams(query)
      sp.delete('store'); sp.delete('store_id')
      const qs = sp.toString()
      cfg.url = qs ? `${path}?${qs}` : path
    }

    return cfg
  })

  api.interceptors.response.use(
    res => {
      const loading = useLoading()
      const isKDS   = /\/billing\/kds\//.test(res.config?.url || '')
      const silent  = isKDS || res.config?.headers?.['X-Silent'] === '1' || res.config?.meta?.silent
      if (!silent) { loading.end(); NProgress.done() }
      return res
    },
    err => {
      const loading = useLoading()
      const url    = err.config?.url || ''
      const isKDS  = /\/billing\/kds\//.test(url)
      const silent = isKDS || err.config?.headers?.['X-Silent'] === '1' || err.config?.meta?.silent
      if (!silent) { loading.end(); NProgress.done() }

      if (err.response?.status === 401) {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(STORE_KEY)
        delete api.defaults.headers.common.Authorization
        const isAuthUrl = DEFAULT_SKIP_AUTH.some(p => url.includes(p))
        if (!isAuthUrl && location.pathname !== '/login') {
          const next = encodeURIComponent(location.pathname + location.search)
          location.assign(`/login?next=${next}`)
        }
      }
      return Promise.reject(err)
    }
  )
}
