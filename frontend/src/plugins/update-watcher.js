// src/plugins/update-watcher.js
import { isNewerAvailable, hardReload, startVersionWatcher } from '@/utils/version-check'
import { showUpdatingOverlay } from '@/utils/splash'

export async function setupUpdateWatcher() {
  // 起動時チェック
  if (await isNewerAvailable()) {
    showUpdatingOverlay();
    setTimeout(() => hardReload(), 600);
    return () => {};
  }
  // 滞在中ポーリング（10分）
  const stop = startVersionWatcher({
    intervalMs: 10 * 60 * 1000,
    onNew: () => {
      showUpdatingOverlay();
      setTimeout(() => hardReload(), 300);
    },
  });
  return stop;
}
