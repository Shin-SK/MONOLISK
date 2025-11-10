// src/stores/storeScope.js
export function notifyStoreChanged (sid) {
  window.dispatchEvent(new CustomEvent('store:changed', { detail: { sid: String(sid) } }))
}

export function listenStoreChanged (handler) {
  window.addEventListener('store:changed', handler)
  return () => window.removeEventListener('store:changed', handler)
}

export function getPinnedStoreId () {
  return localStorage.getItem('store_id') || ''
}
