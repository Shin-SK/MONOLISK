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
