// src/utils/offcanvas-scroll-guard.js  （差し替え）
let openCount = 0
let startY = 0

const closestOffcanvas = (el) => el.closest?.('.offcanvas')

const blockBgWheel = (e) => {
	if (openCount > 0 && !closestOffcanvas(e.target)) e.preventDefault()
}

const onTouchStart = (e) => { if (openCount > 0) startY = e.touches?.[0]?.clientY ?? 0 }

const onTouchMove = (e) => {
	if (openCount === 0) return
	const oc = closestOffcanvas(e.target)
	// 背景なら即ブロック
	if (!oc) { e.preventDefault(); return }

	// オフキャンバス内：境界バウンス時だけブロックしてチェーンを止める
	const scroller = oc.querySelector('.offcanvas-body') || oc
	const currY = e.touches?.[0]?.clientY ?? 0
	const dy = currY - startY
	const atTop = scroller.scrollTop <= 0
	const atBottom = scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 1
	if ((atTop && dy > 0) || (atBottom && dy < 0)) e.preventDefault()
}

export function installOffcanvasScrollGuard(){
	document.addEventListener('shown.bs.offcanvas', () => { openCount++ }, false)
	document.addEventListener('hidden.bs.offcanvas', () => { openCount = Math.max(0, openCount-1) }, false)
	document.addEventListener('touchstart', onTouchStart, { passive:false })
	document.addEventListener('touchmove',  onTouchMove,  { passive:false })
	document.addEventListener('wheel',      blockBgWheel, { passive:false })
}
