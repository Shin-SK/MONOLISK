// utils/offcanvas.js
import { Offcanvas } from 'bootstrap'

// 任意の offcanvas を開く（#id 文字列 or 要素どちらでもOK）
export function openOffcanvas(target) {
  const el = typeof target === 'string' ? document.querySelector(target) : target
  if (!el) return
  Offcanvas.getOrCreateInstance(el).show()
}

// 任意の offcanvas を閉じる
export function closeOffcanvas(target) {
  const el = typeof target === 'string' ? document.querySelector(target) : target
  if (!el) return
  const inst = Offcanvas.getInstance(el)
  inst?.hide()
}

// 画面上で開いている offcanvas を“全部”閉じる（保険）
export function closeAllOffcanvas() {
  document.querySelectorAll('.offcanvas.show').forEach(el => {
    Offcanvas.getInstance(el)?.hide()
  })
}

// 旧 openSidebar/closeSidebar の後方互換（優先順で解決）
function resolveDefaultId() {
  return (
    document.querySelector('#managerSidebar') ||
    document.querySelector('#staffSidebar')   ||
    document.querySelector('#appSidebar')
  )
}

export function openSidebar() {
  const el = resolveDefaultId()
  if (el) Offcanvas.getOrCreateInstance(el).show()
}

export function closeSidebar() {
  const el = resolveDefaultId()
  if (el) Offcanvas.getInstance(el)?.hide()
}

// 旧 closeSidebarThen の汎用版
export function hideThen(target, cb = () => {}) {
  const el = typeof target === 'string' ? document.querySelector(target) : (target || resolveDefaultId())
  if (!el) return cb()
  const inst = Offcanvas.getInstance(el) || Offcanvas.getOrCreateInstance(el)
  if (!el.classList.contains('show')) return cb()
  const onHidden = () => {
    el.removeEventListener('hidden.bs.offcanvas', onHidden)
    cb()
  }
  el.addEventListener('hidden.bs.offcanvas', onHidden)
  inst.hide()
}
