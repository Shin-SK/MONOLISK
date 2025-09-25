// utils/sidebar.js
// 目的：開く/閉じる/遷移 だけを安全に共通化（Backdropや多重管理は一切しない）

function _oc(el) {
  try { return window.bootstrap?.Offcanvas?.getOrCreateInstance(el) } catch { return null }
}

// ctx: HTMLElement | '#id' | '.selector' | MouseEvent | undefined
function _resolve(ctx) {
  if (ctx instanceof HTMLElement) return ctx
  if (ctx?.target instanceof HTMLElement) {
    // クリックイベントなら、近い offcanvas を辿る
    const fromEvt = ctx.target.closest('.offcanvas')
    if (fromEvt) return fromEvt
  }
  if (typeof ctx === 'string') {
    // '#id' かセレクタを許容
    return document.querySelector(ctx)
  }
  // フォールバック：開いてるもの or 最初の offcanvas
  return document.querySelector('.offcanvas.show') || document.querySelector('.offcanvas')
}

export function openSidebar(ctx = '#managerSidebar') {
  const el = _resolve(ctx); if (!el) return
  const inst = _oc(el)
  inst ? inst.show() : el.classList.add('show')
}

export function closeSidebar(ctx = '#managerSidebar') {
  const el = _resolve(ctx); if (!el) return
  const inst = _oc(el)
  inst ? inst.hide() : el.classList.remove('show')
}

/**
 * 使い方（RouterLink）：
 * @click.prevent="go(router, {name:'xxx'}, '#managerSidebar', route.fullPath)"
 * もしくは @click.prevent="go(router, {name:'xxx'}, $event, route.fullPath)"
 */
export async function go(router, to, ctx, currentPath = '') {
  const el = _resolve(ctx)
  const resolved = router.resolve(to)

  // 同一路線なら閉じるだけ
  if (currentPath === resolved.fullPath) {
    if (el) closeSidebar(el)
    return
  }

  // 先に閉じる → にゅるっと遷移（待ち合わせはしない。アニメはBootstrap任せ）
  if (el) closeSidebar(el)
  await router.push(resolved)
}

// 互換用（今のレイアウトから呼ばれても何もしない）
export function initSidebar(/* id */) { /* no-op */ }
