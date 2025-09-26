// src/utils/bsOffcanvas.js
// ※ bootstrap.bundle は main.js で一度だけ import 済み前提
let openInstance = null;

function getInstance(el) {
  const target = typeof el === 'string' ? document.querySelector(el) : el;
  if (!target) return null;
  const bs = window.bootstrap;
  return bs?.Offcanvas.getOrCreateInstance(target, {
    backdrop: true,    // 要件2
    scroll:   false,   // 要件3（ロック）
    keyboard: true
  }) || null;
}

export function openOffcanvas(selector) {
  const inst = getInstance(selector);
  if (!inst) return;
  // 常に1つだけ（要件15）
  if (openInstance && openInstance !== inst) openInstance.hide();
  inst.show();
  openInstance = inst;
}

export function closeOffcanvas(selector) {
  const inst = selector ? getInstance(selector) : openInstance;
  inst?.hide();
  if (!selector || inst === openInstance) openInstance = null;
}

export function closeAnyOpenOffcanvas() {
  closeOffcanvas(); // 何か開いていれば閉じる
}

export function installAutoCloseOnRoute(router) {
  // ルート遷移「完了後」に必ず閉じる（要件4-②）
  router.afterEach(() => closeAnyOpenOffcanvas());
}
