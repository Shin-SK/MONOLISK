// src/plugins/update-watcher.js
import { isNewerAvailable, hardReload, startVersionWatcher } from '@/utils/version-check'
import { showUpdatingOverlay } from '@/utils/splash'

export async function setupUpdateWatcher() {
  // 起動時に必ずバージョンチェック → 不一致なら即座にSW削除+リロード
  const needsUpdate = await isNewerAvailable();
  
  if (needsUpdate) {
    console.log('[update-watcher] 新しいバージョンを検知、更新を適用します');
    showUpdatingOverlay();
    
    // Service Worker と Cache を並列削除（高速化）
    const cleanupTasks = [];
    
    if ('serviceWorker' in navigator) {
      cleanupTasks.push(
        navigator.serviceWorker.getRegistrations()
          .then(regs => Promise.all(regs.map(r => r.unregister())))
          .then(() => console.log('[update-watcher] Service Worker を削除しました'))
          .catch(e => console.warn('[update-watcher] SW unregister failed:', e))
      );
    }
    
    if ('caches' in window) {
      cleanupTasks.push(
        caches.keys()
          .then(keys => Promise.all(keys.map(k => caches.delete(k))))
          .then(() => console.log('[update-watcher] キャッシュをクリアしました'))
          .catch(e => console.warn('[update-watcher] cache clear failed:', e))
      );
    }
    
    // 並列実行後、300ms後にリロード
    await Promise.all(cleanupTasks);
    setTimeout(() => {
      console.log('[update-watcher] リロードします');
      location.reload();
    }, 300);
    
    return () => {};
  }
  
  console.log('[update-watcher] バージョンは最新です');
  
  // ポーリングは削除（途中でいきなりリロードされるのを防ぐ）
  // 次回起動時に必ず最新版がチェックされるので実用上問題なし
  return () => {};
}
