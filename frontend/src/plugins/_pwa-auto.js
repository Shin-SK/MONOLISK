// src/plugin/pwa-auto.js
import { registerSW } from 'virtual:pwa-register'

// SWを即登録
registerSW({ immediate: true })

// 新SWがアクティブになったら一度だけリロード
let reloaded = false
navigator.serviceWorker?.addEventListener('controllerchange', () => {
  if (reloaded) return
  reloaded = true
  window.location.reload()
})
