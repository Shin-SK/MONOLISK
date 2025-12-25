// src/api/interceptors.js
import { useLoading } from '@/stores/useLoading'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// スピナーは独自表示にするのでNProgressのスピナーは無効化
NProgress.configure({ showSpinner: false })

const TOKEN_KEY = 'token'
const STORE_KEY = 'store_id'
const getToken   = () => localStorage.getItem(TOKEN_KEY)
const getStoreId = () => localStorage.getItem(STORE_KEY)

// CSRF トークンを Cookie から取得
function getCsrfToken() {
  const name = 'csrftoken'
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return null
}

// 認証スキップ対象（含まれていれば Authorization を付けない）
const DEFAULT_SKIP_AUTH = [
  'dj-rest-auth/login',
  'dj-rest-auth/logout',
  'dj-rest-auth/registration',
  'auth/registration',
  'dj-rest-auth/password',
  'dj-rest-auth/password/reset',
]

// Store 非依存（X-Store-Id を付けない）
const STORE_INDEPENDENT_PREFIXES = [
  'me',
  'accounts/me',
  'dj-rest-auth/login',
  'dj-rest-auth/logout',
  'dj-rest-auth/registration',
  'auth/registration',
  'dj-rest-auth/password',
  'dj-rest-auth/password/reset',
  'dj-rest-auth/user',
  'billing/stores/my',
]

// 'api/dj-rest-auth/login/' → 'dj-rest-auth/login'
function normalizePathLike(p) {
  return (p || '').replace(/^\/+|\/+$/g, '').replace(/^api\/+/, '').replace(/\/+$/,'')
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

function shouldSkipAuth(rawUrl='') {
  const s = normalizePathLike(rawUrl)
  return DEFAULT_SKIP_AUTH.some(pref => {
    const n = normalizePathLike(pref)
    return s === n || s.startsWith(n + '/')
  })
}

export function wireInterceptors(api) {
  // ===== Request =====
  api.interceptors.request.use(cfg => {
    const loading = useLoading()
    const isKDS   = /\/billing\/kds\//.test(cfg.url || '')
    const silent  = isKDS || cfg.headers?.['X-Silent'] === '1' || cfg.meta?.silent
    if (!silent) { loading.start(); NProgress.start() }

    // FormData の時は Content-Type はブラウザに任せる
    if (cfg.data instanceof FormData) delete cfg.headers?.['Content-Type']

    // Authorization（スキップ対象を除く）
    if (!shouldSkipAuth(cfg.url || '')) {
      const t = getToken()
      if (t) (cfg.headers ||= {}).Authorization = `Token ${t}`
    }

    // CSRF トークン（POST/PUT/DELETE/PATCH の場合に必要）
    const method = (cfg.method || 'get').toLowerCase()
    if (['post', 'put', 'delete', 'patch'].includes(method)) {
      const csrfToken = getCsrfToken()
      if (csrfToken) {
        (cfg.headers ||= {})['X-CSRFToken'] = csrfToken
      }
    }

    // X-Store-Id（Store 非依存パス以外は必須）
    const p = pathFrom(cfg, api.defaults.baseURL)
    if (!isStoreIndependentPath(p)) {
      const sid = cfg.meta?.overrideStoreId || getStoreId()  // ★ meta.overrideStoreId を優先
      cfg.headers ||= {}
      const hasOverride = !!(cfg.headers['X-Store-Id'] || cfg.headers['X-Store-ID'])
      if (!hasOverride && sid) {
        cfg.headers['X-Store-Id'] = String(sid)
        cfg.headers['X-Store-ID'] = String(sid)
        if (cfg.meta?.overrideStoreId) {
          console.log('[api] X-Store-Id overridden to:', sid, 'for url:', cfg.url)
        }
      } else if (!hasOverride && !sid) {
        console.warn('[api] X-Store-Id missing for Store-Locked API:', p)
      }
    }

    // 残骸クエリを除去
    if (cfg.params) { delete cfg.params.store_id; delete cfg.params.store }
    if (typeof cfg.url === 'string' && cfg.url.includes('?')) {
      const [path, query] = cfg.url.split('?')
      const sp = new URLSearchParams(query)
      sp.delete('store'); sp.delete('store_id')
      const qs = sp.toString()
      cfg.url = qs ? `${path}?${qs}` : path
    }

    // if (import.meta.env.DEV) {
    //   console.log('[API:REQ]', cfg.method?.toUpperCase(), cfg.url, {
    //     x_store_id: cfg.headers?.['X-Store-Id'] || cfg.headers?.['x-store-id'],
    //     auth: !!cfg.headers?.Authorization
    //   })
    // }

    if ((cfg.method || 'get').toLowerCase() === 'delete') {
      cfg.cache = false
    }
    return cfg
  })

  // ===== Response =====
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

      // 401 → 認証クリアしてログインへ
      if (err.response?.status === 401) {
        console.warn('[401] on', err.config?.url, '→ clearAuth')
        localStorage.removeItem(TOKEN_KEY)
        // ★ store_id は消さない
        delete api.defaults.headers.common?.Authorization
        const next = encodeURIComponent(location.pathname + location.search)
        if (location.pathname !== '/login') location.assign(`/login?next=${next}`)
      }
      return Promise.reject(err)
    }
  )
}
