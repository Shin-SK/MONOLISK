// src/utils/splash.js
let showTimer = null;

export function showSplash(contentHTML) {
  const el = document.getElementById('splash');
  if (!el) return;
  el.classList.remove('hide');
  if (contentHTML) el.innerHTML = contentHTML;
}

export function finishSplash() {
  if (showTimer) { clearTimeout(showTimer); showTimer = null; }
  const appEl = document.getElementById('app');
  appEl?.classList.add('app-shown');
  appEl?.classList.remove('app-hidden');

  const splash = document.getElementById('splash');
  if (splash) {
    splash.classList.add('hide');
    splash.addEventListener('transitionend', () => splash.remove(), { once: true });
  }
}

export function scheduleFinishSplash(extraMs = 500) {
  if (showTimer) clearTimeout(showTimer);
  showTimer = setTimeout(() => finishSplash(), extraMs);
}

export function showUpdatingOverlay() {
  showSplash(`
    <div style="display:flex;flex-direction:column;align-items:center;gap:8px;">
      <div class="spinner-border" role="status"></div>
      <div class="fw-bold">アップデート反映中…</div>
      <div class="small text-muted">数秒お待ちください</div>
    </div>
  `);
}
