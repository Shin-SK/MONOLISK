// src/plugins/pwa.js
// PWA更新方式: 主=onNeedRefresh / 従=version.json(起動時フォールバック)
import { registerSW } from 'virtual:pwa-register'

const BANNER_ID = 'update-banner'
const OVERLAY_ID = 'update-overlay'
const SW_TIMEOUT = 8000 // controllerchange 待機タイムアウト(ms)
let updateNowFn = null
let _updateAvailable = false

/** 更新が利用可能かどうか */
export function isUpdateAvailable () { return _updateAvailable }

/** 外部から更新フラグを立てる（update-watcher用フォールバック） */
export function markUpdateAvailable () {
  if (_updateAvailable) return
  _updateAvailable = true
  showBanner()
}

// ─── 通知バナー（画面下部に固定、操作を遮らない）───
function showBanner () {
  if (document.getElementById(BANNER_ID)) return
  const el = document.createElement('div')
  el.id = BANNER_ID
  el.innerHTML = `
    <div class="ub-inner">
      <div class="ub-text">
        <div class="ub-title">新しいバージョンがあります</div>
        <div class="ub-sub">この端末が空いたタイミングで更新してください</div>
      </div>
      <button class="ub-btn" id="ub-apply">今すぐ更新</button>
      <button class="ub-close" id="ub-close" aria-label="閉じる">&times;</button>
    </div>
  `
  const style = document.createElement('style')
  style.textContent = `
#${BANNER_ID}{
  position:fixed; bottom:0; left:0; right:0; z-index:2147483000;
  padding:12px 16px; background:#111; color:#fff;
  font-size:13px; box-shadow:0 -4px 20px rgba(0,0,0,.15);
  animation:ub-slide .3s ease;
}
@keyframes ub-slide{from{transform:translateY(100%)}to{transform:translateY(0)}}
#${BANNER_ID} .ub-inner{
  display:flex; align-items:center; gap:12px; max-width:600px; margin:0 auto;
}
#${BANNER_ID} .ub-text{ flex:1; }
#${BANNER_ID} .ub-title{ font-weight:600; font-size:14px; }
#${BANNER_ID} .ub-sub{ opacity:.7; margin-top:2px; }
#${BANNER_ID} .ub-btn{
  flex-shrink:0; padding:6px 16px; border:none; border-radius:6px;
  background:#fff; color:#111; font-weight:600; font-size:13px; cursor:pointer;
}
#${BANNER_ID} .ub-btn:active{ opacity:.8; }
#${BANNER_ID} .ub-close{
  flex-shrink:0; background:none; border:none; color:#fff; font-size:20px;
  cursor:pointer; opacity:.6; padding:0 4px;
}
#${BANNER_ID} .ub-close:hover{ opacity:1; }
  `
  document.head.appendChild(style)
  document.body.appendChild(el)

  document.getElementById('ub-apply')?.addEventListener('click', () => applyUpdateNow())
  document.getElementById('ub-close')?.addEventListener('click', () => dismissBanner())
}

function dismissBanner () {
  const el = document.getElementById(BANNER_ID)
  if (el) el.remove()
}

// ─── 更新適用中オーバーレイ（手動更新時のみ表示）───
function ensureOverlay (msg = 'アップデートを適用中…') {
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
  position:fixed; inset:0; z-index:2147483001;
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
  }
  el.style.display = 'flex'
}

function saveResumePoint () {
  const url = new URL(window.location.href)
  url.searchParams.delete('v')
  const p = url.pathname + url.search + url.hash
  sessionStorage.setItem('__resume_to', p)
}

/** controllerchange を待つ（タイムアウト付き） */
function waitForControllerChange (ms) {
  return new Promise(resolve => {
    const sw = navigator.serviceWorker
    if (!sw) { resolve(false); return }
    const timer = setTimeout(() => { sw.removeEventListener('controllerchange', ok); resolve(false) }, ms)
    function ok () { clearTimeout(timer); resolve(true) }
    sw.addEventListener('controllerchange', ok, { once: true })
  })
}

export function restoreRouteIfNeeded (router) {
  const p = sessionStorage.getItem('__resume_to')
  if (!p) return
  sessionStorage.removeItem('__resume_to')
  if (router && typeof router.replace === 'function') {
    router.replace(p).catch(() => {})
  } else {
    if ((location.pathname + location.search + location.hash) !== p) {
      location.replace(p)
    }
  }
}

// ─── PWA セットアップ ───
export function setupPWA () {
  const updateFn = registerSW({
    immediate: true,
    onNeedRefresh () {
      _updateAvailable = true
      showBanner()
    },
    onOfflineReady () { /* noop */ },
    onRegisterError (e) { console.warn('[pwa] register error:', e) }
  })
  updateNowFn = updateFn
}

/** ユーザー操作で「今すぐ更新」を実行 */
export async function applyUpdateNow () {
  if (!_updateAvailable) return

  _updateAvailable = false
  dismissBanner()
  ensureOverlay('アップデートを適用中…')
  saveResumePoint()

  // 1. updateNowFn() で新SWを activate させる
  try {
    if (typeof updateNowFn === 'function') await updateNowFn(true)
  } catch (_) {}

  // 2. controllerchange を待つ
  const ok = await waitForControllerChange(SW_TIMEOUT)

  if (ok) {
    // 成功: 新SWが制御を取った → リロード
    location.reload()
  } else {
    // タイムアウト: フォールバックとしてリロードだけ試みる
    removeOverlay()
    showFailBanner()
  }
}

function removeOverlay () {
  const el = document.getElementById(OVERLAY_ID)
  if (el) el.remove()
}

function showFailBanner () {
  if (document.getElementById(BANNER_ID)) return
  const el = document.createElement('div')
  el.id = BANNER_ID
  el.innerHTML = `
    <div class="ub-inner">
      <div class="ub-text">
        <div class="ub-title">更新の適用に失敗しました</div>
        <div class="ub-sub">ページを再読み込みしてください</div>
      </div>
      <button class="ub-btn" id="ub-reload">再読み込み</button>
      <button class="ub-close" id="ub-close2" aria-label="閉じる">&times;</button>
    </div>
  `
  document.body.appendChild(el)
  document.getElementById('ub-reload')?.addEventListener('click', () => location.reload())
  document.getElementById('ub-close2')?.addEventListener('click', () => dismissBanner())
}
