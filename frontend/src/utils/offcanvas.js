// utils/offcanvas.js
// 目的: 二重バックドロップ対策として『Backdrop操作は一切しない』。
//       既存を閉じてから新規を開く、の最小ロジックだけ残す。

import Offcanvas from 'bootstrap/js/dist/offcanvas'

let currentEl   = null
let currentInst = null
let opening     = false

const q  = (s) => document.querySelector(s)
const qa = (s) => Array.from(document.querySelectorAll(s))
const isShown = (el) => !!el && el.classList.contains('show')

const SIDEBAR_IDS = ['#managerSidebar','#ownerSidebar','#staffSidebar','#castSidebar','#appSidebar']

function resolveEl(target) {
  if (target && typeof target !== 'string') return target
  if (typeof target === 'string') return q(target)

  const opened = qa('.offcanvas.show')
  if (opened.length === 1) return opened[0]

  const existing = SIDEBAR_IDS.map(id => q(id)).filter(Boolean)
  if (existing.length === 1) return existing[0]

  console.warn('[offcanvas] resolveEl(): target不明。#id を渡してください。 candidates=', existing.map(e => e.id))
  return null
}

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

// ★ Backdrop 触らず、単に他を閉じきってから開く
async function hideOthers(except) {
  for (const el of qa('.offcanvas.show')) {
    if (el === except) continue
    Offcanvas.getInstance(el)?.hide()
    await waitEvent(el, 'hidden.bs.offcanvas')
  }
}

/* =========== Public API =========== */

export async function openOffcanvas(target) {
  const el = resolveEl(target)
  if (!el) return
  if (isShown(el)) { currentEl = el; currentInst = Offcanvas.getOrCreateInstance(el); return }

  if (opening) return
  opening = true
  try {
    await hideOthers(el)  // 既存を確実に閉じる（BackdropはBootstrap任せ）
    currentInst = Offcanvas.getOrCreateInstance(el)
    currentEl   = el

    el.addEventListener('hidden.bs.offcanvas', () => {
      if (currentEl === el) { currentEl = null; currentInst = null }
    }, { once: true })

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
}

/** 旧API互換 */
export const openSidebar  = openOffcanvas
export const closeSidebar = closeOffcanvas

/**
 * グローバル初期化（data-apiでも「他を閉じてから開く」を保証）
 * ※ Backdropの手動調整は行わない
 */
export function installOffcanvasSingleton() {
  document.addEventListener('show.bs.offcanvas',  async (ev) => { await hideOthers(ev.target) })
}
