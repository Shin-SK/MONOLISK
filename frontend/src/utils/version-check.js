// src/utils/version-check.js
import { APP_VERSION } from '@/version.gen.js'

export async function fetchServerVersion() {
  try {
    const res = await fetch('/version.json?ts=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error('status ' + res.status);
    return await res.json(); // { app_version, git_sha, build_at }
  } catch (e) {
    console.warn('[version] fetch error', e);
    return null;
  }
}

export async function isNewerAvailable() {
  const sv = await fetchServerVersion();
  if (!sv || !sv.app_version) return false;
  return String(sv.app_version) !== String(APP_VERSION);
}

export async function hardReload() {
  if ('serviceWorker' in navigator) {
    try {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map(r => r.unregister()));
    } catch {}
  }
  if ('caches' in window) {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map(k => caches.delete(k)));
    } catch {}
  }
  location.reload();
}

/** 起動時 + 滞在中ポーリング
 * @param {Object} opt
 * @param {number} opt.intervalMs  ポーリング間隔(ms)
 * @param {function} opt.onNew      新版検知時に呼ばれる
 * @returns {function} stop
 */
export function startVersionWatcher({ intervalMs = 10 * 60 * 1000, onNew } = {}) {
  let stopped = false;
  let timer = null;

  async function tick() {
    if (stopped) return;
    try {
      if (await isNewerAvailable()) {
        onNew && onNew();
        return; // onNew 内で reload する想定
      }
    } finally {
      if (!stopped) timer = setTimeout(tick, intervalMs);
    }
  }
  tick();
  return () => { stopped = true; if (timer) clearTimeout(timer); };
}
