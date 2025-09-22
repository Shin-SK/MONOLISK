// utils/offcanvas.js
import Offcanvas from 'bootstrap/js/dist/offcanvas'

/** 現在開いている Offcanvas を単一管理（重複 show 抑止） */
let currentEl   = null
let currentInst = null
let opening     = false

const q  = (s) => document.querySelector(s)
const qa = (s) => Array.from(document.querySelectorAll(s))
const isShown = (el) => !!el && el.classList.contains('show')

/** プロジェクト内のサイドバー候補（存在順に評価） */
const SIDEBAR_IDS = [
  '#managerSidebar',
  '#ownerSidebar',
  '#staffSidebar',
  '#castSidebar',
  '#appSidebar',
]

/**
 * resolveEl:
 *  1) target が Element ならそれ
 *  2) target が string なら querySelector
 *  3) 画面に “開いている offcanvas” が 1つだけならそれ（最優先）
 *  4) DOMに存在する候補IDのうち “唯一” のものがあればそれ
 *  5) どれでもなければ null（暗黙決め打ちはしない）
 */
function resolveEl(target) {
  if (target && typeof target !== 'string') return target
  if (typeof target === 'string') return q(target)

  const opened = qa('.offcanvas.show')
  if (opened.length === 1) return opened[0]         // ← 現在開いているもの

  const existing = SIDEBAR_IDS.map(id => q(id)).filter(Boolean)
  if (existing.length === 1) return existing[0]     // ← 候補が唯一

  // ここで暗黙にどれかを選ばない（誤動作の温床）
  console.warn('[offcanvas] resolveEl(): target不明。明示的に #id を渡してください。 candidates=', existing.map(e => e.id))
  return null
}

/** 指定イベント待ち（タイムアウト付） */
function waitEvent(el, name, timeout = 600) {
  return new Promise((resolve) => {
    let done = false
    const t = setTimeout(() => { if (!done) resolve() }, timeout)
    el.addEventListener(name, () => {
      if (done) return
      done = true
      clearTimeout(t)
      resolve()
    }, { once: true })
  })
}

/** Backdrop と body 状態の正規化（常に 0 or 1 枚） */
function normalizeBackdrop() {
  const opened = qa('.offcanvas.show').length
  const backs  = qa('.offcanvas-backdrop')
  if (opened === 0) {
    backs.forEach(b => b.remove())
    document.body.classList.remove('modal-open','offcanvas-backdrop','overflow-hidden')
    document.body.style.removeProperty('padding-right')
    return
  }
  if (backs.length > 1) backs.slice(0, backs.length - 1).forEach(b => b.remove())
}

/** 他を全部閉じて hidden を待つ（新規 show 前に必ず実行） */
async function hideOthers(except) {
  for (const el of qa('.offcanvas.show')) {
    if (el === except) continue
    Offcanvas.getInstance(el)?.hide()
    await waitEvent(el, 'hidden.bs.offcanvas')
  }
  normalizeBackdrop()
}

/* =========== Public API =========== */

export async function openOffcanvas(target) {
  const el = resolveEl(target)
  if (!el) return
  if (isShown(el)) { currentEl = el; currentInst = Offcanvas.getOrCreateInstance(el); return }

  if (opening) return
  opening = true
  try {
    await hideOthers(el)        // ★ まず既存を確実に閉じる
    normalizeBackdrop()

    currentInst = Offcanvas.getOrCreateInstance(el)
    currentEl   = el

    el.addEventListener('hidden.bs.offcanvas', () => {
      if (currentEl === el) { currentEl = null; currentInst = null }
      normalizeBackdrop()
    }, { once: true })
    el.addEventListener('shown.bs.offcanvas', normalizeBackdrop, { once: true })

    currentInst.show()
  } finally { setTimeout(() => { opening = false }, 0) }
}

export function closeOffcanvas(target) {
  const el = resolveEl(target ?? currentEl)
  if (!el) return
  Offcanvas.getInstance(el)?.hide()
}

export function closeAllOffcanvas() {
  qa('.offcanvas.show').forEach(el => Offcanvas.getInstance(el)?.hide())
  normalizeBackdrop()
}

/** 旧API互換。引数なし呼び出しは非推奨（resolveEl()がnullならNO-OP） */
export function openSidebar(target)  { return openOffcanvas(target) }
export function closeSidebar(target) { return closeOffcanvas(target) }

/**
 * グローバル初期化（data-api でも一貫挙動）：
 *  - show 直前に他を閉じる
 *  - shown/hidden 後に backdrop 正規化
 *  - さらに MutationObserver で“常に1枚”を保証
 */
export function installOffcanvasSingleton() {
  document.addEventListener('show.bs.offcanvas',  async (ev) => { await hideOthers(ev.target) })
  document.addEventListener('shown.bs.offcanvas', normalizeBackdrop)
  document.addEventListener('hidden.bs.offcanvas',normalizeBackdrop)
  normalizeBackdrop()
  const mo = new MutationObserver(normalizeBackdrop)
  mo.observe(document.body, { childList: true })
}
