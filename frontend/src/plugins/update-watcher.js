// src/plugins/update-watcher.js
// 起動時のバージョンチェック → 通知のみ（強制reloadしない）
import { isNewerAvailable } from '@/utils/version-check'
import { markUpdateAvailable } from '@/plugins/pwa'

export async function setupUpdateWatcher() {
  try {
    const needsUpdate = await isNewerAvailable()
    if (needsUpdate) {
      markUpdateAvailable()
    }
  } catch (e) {
    console.warn('[update-watcher] version check failed:', e)
  }
}
