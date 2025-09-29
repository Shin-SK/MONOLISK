export function isStandalone () {
  return window.matchMedia?.('(display-mode: standalone)')?.matches
      || window.navigator.standalone === true; // iOS PWA
}

export function openManual (url, router) {
  if (isStandalone() && router) {
    router.push({ name: 'manual-viewer', query: { src: url } })
  } else {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}
