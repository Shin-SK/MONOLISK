// src/plugins/update-watcher.js
import { isNewerAvailable, hardReload, startVersionWatcher } from '@/utils/version-check'
import { showUpdatingOverlay } from '@/utils/splash'

export async function setupUpdateWatcher() {
  // 起動時に必ずバージョンチェック → 不一致なら即座にSW削除+リロード
  const needsUpdate = await isNewerAvailable();
  
  if (needsUpdate) {
    console.log('[update-watcher] 新しいバージョンを検知、更新を適用します');
    showUpdatingOverlay();
    
    // Service Worker を完全削除してからリロード（ブラウザ利用が主体なのでオフライン対応より更新優先）
    if ('serviceWorker' in navigator) {
      try {
        const regs = await navigator.serviceWorker.getRegistrations();
        await Promise.all(regs.map(r => r.unregister()));
        console.log('[update-watcher] Service Worker を削除しました');
      } catch (e) {
        console.warn('[update-watcher] SW unregister failed:', e);
      }
    }
    
    // キャッシュも削除
    if ('caches' in window) {
      try {
        const keys = await caches.keys();
        await Promise.all(keys.map(k => caches.delete(k)));
        console.log('[update-watcher] キャッシュをクリアしました');
      } catch (e) {
        console.warn('[update-watcher] cache clear failed:', e);
      }
    }
    
    // 600ms後にハードリロード（オーバーレイ表示時間確保）
    setTimeout(() => {
      console.log('[update-watcher] リロードします');
      location.reload();
    }, 600);
    
    return () => {};
  }
  
  console.log('[update-watcher] バージョンは最新です、ポーリングを開始します');
  
  // 滞在中ポーリング（10分）
  const stop = startVersionWatcher({
    intervalMs: 10 * 60 * 1000,
    onNew: () => {
      console.log('[update-watcher] ポーリングで新バージョンを検知');
      showUpdatingOverlay();
      setTimeout(() => hardReload(), 300);
    },
  });
  return stop;
}
