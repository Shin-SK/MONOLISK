// utils/offcanvas.js
import { Offcanvas } from 'bootstrap'

export function openSidebar () {
  Offcanvas.getOrCreateInstance('#appSidebar').show()
}

export function closeSidebar () {
  Offcanvas.getInstance('#appSidebar')?.hide()
}

export function closeSidebarThen (cb = () => {}) {
  const oc = Offcanvas.getInstance('#appSidebar')
  if (!oc) return cb()                    // インスタンス無し＝閉じている

  if (!oc._isShown) return cb()           // 既に閉じている

  const onHidden = () => {
    oc._element.removeEventListener('hidden.bs.offcanvas', onHidden)
    cb()
  }
  oc._element.addEventListener('hidden.bs.offcanvas', onHidden)
  oc.hide()
}
