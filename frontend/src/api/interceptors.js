// src/api/interceptors.js
import { useLoading } from '@/stores/useLoading'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

const TOKEN_KEY = 'token'
const STORE_KEY = 'store_id'
const getToken   = () => localStorage.getItem(TOKEN_KEY)
const getStoreId = () => localStorage.getItem(STORE_KEY)

// 末尾スラッシュに依存しないよう、すべて「トレーリングなし」で管理
const DEFAULT_SKIP_AUTH = [
  'dj-rest-auth/login',
  'dj-rest-auth/logout',
  'dj-rest-auth/registration',
  'auth/registration',
  'dj-rest-auth/password',
  'dj-rest-auth/password/reset',
  'dj-rest-auth/user',
]

// ★ Store非依存パス（X-Store-Id を付けない＆警告もしない）
const STORE_INDEPENDENT_PREFIXES = [
  'me',                    // /api/me
  'dj-rest-auth/login',
  'dj-rest-auth/logout',
  'dj-rest-auth/registration',
  'auth/registration',
  'dj-rest-auth/password',
  'dj-rest-auth/password/reset',
  'dj-rest-auth/user',
  'billing/stores/my',     // /api/billing/stores/my
]

function normalizePathLike(p) {
  // 'api/dj-rest-auth/login/' → 'dj-rest-auth/login'
  return (p || '')
    .replace(/^\/+|\/+$/g, '')        // trim slashes both ends
    .replace(/^api\/+/, '')           // drop leading 'api/'
    .replace(/\/+$/,'')               // drop trailing slash
}

function pathFrom(cfg, baseURL='') {
  const urlStr = cfg.url || ''
  try {
    const abs = /^https?:\/\//i.test(urlStr)
      ? new URL(urlStr)
      : new URL(urlStr, (baseURL && /^https?:\/\//i.test(baseURL)) ? baseURL : window.location.origin)
    return abs.pathname.replace(/^\/+|\/+$/g, '')
  } catch {
    return String(urlStr).replace(/^\/+/, '')
  }
}

function isStoreIndependentPath(p){
  const s = normalizePathLike(p)
  return STORE_INDEPENDENT_PREFIXES.some(pref => {
    const n = normalizePathLike(pref)
    return s === n || s.startsWith(n + '/')
  })
}

export function wireInterceptors(api) {
  api.interceptors.request.use(cfg => {
    const loading = useLoading()
    const isKDS   = /\/billing\/kds\//.test(cfg.url || '')
    const silent  = isKDS || cfg.headers?.['X-Silent'] === '1' || cfg.meta?.silent
    if (!silent) { loading.start(); NProgress.start() }

    if (cfg.data instanceof FormData) delete cfg.headers['Content-Type']

    // 認証ヘッダ（ログイン系は除外）
    const raw = cfg.url || ''
    const skipAuth = DEFAULT_SKIP_AUTH.some(p => normalizePathLike(raw).includes(normalizePathLike(p)))
    if (!skipAuth) {
      const t = getToken()
      if (t) cfg.headers.Authorization = `Token ${t}`
    }

    // ★ Store非依存でなければ X-Store-Id
    const p = pathFrom(cfg, api.defaults.baseURL)
    if (!isStoreIndependentPath(p)) {
      const sid = getStoreId()
      if (sid) cfg.headers['X-Store-Id'] = String(sid)
      else console.warn('[api] X-Store-Id missing for Store-Locked API:', p)
    }

    // 残骸クリーニング
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

      // 401 → トークン＆store_idクリアして /login?next=...
      if (err.response?.status === 401) {
		console.warn('[401] on', err.config?.url, '→ clearAuth')
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(STORE_KEY)
        delete api.defaults.headers.common.Authorization
        const next = encodeURIComponent(location.pathname + location.search)
        if (location.pathname !== '/login') location.assign(`/login?next=${next}`)
      }
      return Promise.reject(err)
    }
  )
}
