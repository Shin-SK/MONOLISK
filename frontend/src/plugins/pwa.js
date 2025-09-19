// src/plugins/pwa.js
import { registerSW } from 'virtual:pwa-register'

const OVERLAY_ID = 'update-overlay'
let updateNowFn = null
let reloaded = false

let fallbackTimer = null


function ensureOverlay (msg = 'アップデート中… 数秒で再開します') {
  let el = document.getElementById(OVERLAY_ID)
  if (!el) {
    el = document.createElement('div')
    el.id = OVERLAY_ID
    el.innerHTML = `
      <div class="u-body">
        <div class="u-card">
          <div class="u-spinner" aria-hidden="true"></div>
          <div class="u-msg">${msg}</div>
        </div>
      </div>
    `
    const style = document.createElement('style')
    style.textContent = `
#${OVERLAY_ID}{
  position:fixed; inset:0; z-index:2147483000;
  display:flex; align-items:center; justify-content:center;
  background:rgba(255,255,255,.85); backdrop-filter:saturate(1.2) blur(2px);
}
#${OVERLAY_ID} .u-card{
  display:flex; gap:.75rem; align-items:center;
  padding:1rem 1.25rem; border-radius:12px; background:#fff; box-shadow:0 6px 24px rgba(0,0,0,.12);
  font-size:14px; color:#111;
}
#${OVERLAY_ID} .u-spinner{
  width:18px; height:18px; border-radius:50%;
  border:2px solid #ddd; border-top-color:#111; animation:u-spin 1s linear infinite;
}
@keyframes u-spin{to{transform:rotate(360deg)}}
    `
    document.head.appendChild(style)
    document.body.appendChild(el)
  } else {
    const msgEl = el.querySelector('.u-msg')
    if (msgEl) msgEl.textContent = msg
  }
  el.style.display = 'flex'
  return el
}

function hideOverlay () {
  const el = document.getElementById(OVERLAY_ID)
  if (el) el.style.display = 'none'
}

function saveResumePoint () {
  const p = location.pathname + location.search + location.hash
  sessionStorage.setItem('__resume_to', p)
}

export function restoreRouteIfNeeded (router) {
  const p = sessionStorage.getItem('__resume_to')
  if (!p) return
  sessionStorage.removeItem('__resume_to')
  // 可能ならルーターで復帰、無ければロケーションで
  if (router && typeof router.replace === 'function') {
    router.replace(p).catch(() => {})
  } else {
    if ((location.pathname + location.search + location.hash) !== p) {
      location.replace(p)
    }
  }
}

export function setupPWA () {
  const updateFn = registerSW({
    immediate: true,
    // 新版あり（SW待機）→ すぐ適用へ
    onNeedRefresh () {
      ensureOverlay('アップデート中… 数秒で再開します')
      saveResumePoint()
      // 待機SWを即適用：skipWaiting → controllerchange で再読込
      if (typeof updateNowFn === 'function') updateNowFn()
      if (!fallbackTimer) {
        fallbackTimer = setTimeout(() => {
          const cur = location.pathname + location.search + location.hash
          const sep = location.search ? '&' : '?'
          location.replace(`${cur}${sep}v=${Date.now()}`)
        }, 4000) // 4秒で強制リロード
      }
    },
    onOfflineReady () { /* noop */ },
    onRegisterError (e) { console.warn('[pwa] register error:', e) }
  })
  updateNowFn = updateFn

  // SW適用 → 1回だけハードリロード（index.html は no-store 前提）
  navigator.serviceWorker?.addEventListener('controllerchange', () => {
    if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
    if (reloaded) return
    reloaded = true
    ensureOverlay('アップデート中… 再読み込みしています')
    const cur = location.pathname + location.search + location.hash
    const sep = location.search ? '&' : '?'
    location.replace(`${cur}${sep}v=${Date.now()}`)
  })
}

/** 明示的に「今すぐ更新」を要求（ログイン直後などで使用可） */
export async function applyUpdateNow () {
  try {
    ensureOverlay('アップデートを適用中…')
    saveResumePoint()
    if (!fallbackTimer) {
      fallbackTimer = setTimeout(() => {
        const cur = location.pathname + location.search + location.hash
        const sep = location.search ? '&' : '?'
        location.replace(`${cur}${sep}v=${Date.now()}`)
      }, 4000)
    }
    if (typeof updateNowFn === 'function') await updateNowFn()
  } catch (e) {
    console.warn('[pwa] applyUpdateNow failed:', e)
    hideOverlay()
  }
}
