// Offcanvas と 自前 Modal(.modal.d-block) の両方で
// 背景スクロールを抑止するガード（utils/offcanvas-scroll-guard.js）

export function installOffcanvasScrollGuard(){
	let startY = 0
	const overlaySel = '.offcanvas.show, .modal.d-block, .modal.show'
	const isOpen = () => !!document.querySelector(overlaySel)
	const closestOverlay = (el) => el.closest?.('.offcanvas, .modal')

	const getScroller = (ov) => {
		if (!ov) return null
		// Offcanvas: body優先
		if (ov.classList.contains('offcanvas')) {
			return ov.querySelector('.offcanvas-body') || ov
		}
		// Modal: .modal-dialog-scrollableなら .modal-body をスクロール領域に
		const mb = ov.querySelector('.modal-dialog-scrollable .modal-body')
		return mb || ov.querySelector('.modal-body') || ov
	}

	const onTouchStart = (e) => { if (isOpen()) startY = e.touches?.[0]?.clientY ?? 0 }

	const onTouchMove = (e) => {
		if (!isOpen()) return
		const ov = closestOverlay(e.target)
		// 背景上 → 即ブロック
		if (!ov) { e.preventDefault(); return }

		// オーバーレイ内：境界バウンス時だけブロック（背景へのチェーンを止める）
		const sc = getScroller(ov)
		if (!sc) { e.preventDefault(); return }
		const currY = e.touches?.[0]?.clientY ?? 0
		const dy = currY - startY
		const atTop = sc.scrollTop <= 0
		const atBottom = sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 1
		if ((atTop && dy > 0) || (atBottom && dy < 0)) e.preventDefault()
	}

	const onWheel = (e) => {
		if (isOpen() && !closestOverlay(e.target)) e.preventDefault()
	}

	// iOS対策で passive:false
	document.addEventListener('touchstart', onTouchStart, { passive:false })
	document.addEventListener('touchmove',  onTouchMove,  { passive:false })
	document.addEventListener('wheel',      onWheel,      { passive:false })
}
