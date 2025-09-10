// utils/offcanvas.js
import { Offcanvas } from 'bootstrap'

let _applied = 0
let _lockedY = 0

function lockBody () {
	// すでに自分でロック中ならカウントだけ増やす
	if (_applied > 0) { _applied++; return }
	// 別のロック（例: モーダル）が position:fixed を当てているなら干渉しない
	const alreadyFixed = getComputedStyle(document.body).position === 'fixed'
	if (alreadyFixed) { _applied++; return }

	_lockedY = window.scrollY || document.documentElement.scrollTop || 0
	const sw = window.innerWidth - document.documentElement.clientWidth
	if (sw > 0) document.body.style.paddingRight = `${sw}px`

	document.body.classList.add('offcanvas-open')
	document.body.style.position    = 'fixed'
	document.body.style.top         = `-${_lockedY}px`
	document.body.style.width       = '100%'
	document.body.style.overflow    = 'hidden'
	document.body.style.touchAction = 'none'
	_applied = 1
}

function unlockBody () {
	if (_applied === 0) return
	_applied--
	// ネストしていれば解除しない
	if (_applied > 0) return
	// まだモーダル等でロック中なら触らない
	if (document.body.classList.contains('modal-open')) return

	document.body.classList.remove('offcanvas-open')
	document.body.style.position    = ''
	document.body.style.top         = ''
	document.body.style.width       = ''
	document.body.style.overflow    = ''
	document.body.style.paddingRight= ''
	document.body.style.touchAction = ''
	window.scrollTo(0, _lockedY || 0)
}

// Offcanvasイベントにフック（アプリ起動時に1回呼ぶ）
export function wireOffcanvasBodyLock () {
	document.addEventListener('shown.bs.offcanvas', lockBody)
	document.addEventListener('hidden.bs.offcanvas', unlockBody)
}

// 文字列セレクタ/要素どちらでも受ける
function _getEl (target) {
	return typeof target === 'string' ? document.querySelector(target) : target
}

export function openSidebar (target = '#appSidebar', opts = {}) {
	const el = _getEl(target)
	if (!el) return
	// 背景スクロール禁止を明示
	const oc = Offcanvas.getOrCreateInstance(el, {
		backdrop: true, scroll: false, keyboard: true, ...opts
	})
	oc.show()
}

export function closeSidebar (target = '#appSidebar') {
	const el = _getEl(target)
	if (!el) return
	Offcanvas.getInstance(el)?.hide()
}

/** サイドバーを閉じてから callback を実行 */
export function closeSidebarThen (cb = () => {}, target = '#appSidebar') {
	const el = _getEl(target)
	if (!el) return cb()
	const oc = Offcanvas.getInstance(el)
	if (!oc || !oc._isShown) return cb()
	const onHidden = () => { el.removeEventListener('hidden.bs.offcanvas', onHidden); cb() }
	el.addEventListener('hidden.bs.offcanvas', onHidden)
	oc.hide()
}
