// utils/offcanvas.js
import { Offcanvas } from 'bootstrap'

let _applied = 0
let _lockedY = 0

function lockBody () {
	if (_applied > 0) { _applied++; return }
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
	if (_applied > 0) return
	if (document.body.classList.contains('modal-open')) return

	document.body.classList.remove('offcanvas-open')
	document.body.style.position     = ''
	document.body.style.top          = ''
	document.body.style.width        = ''
	document.body.style.overflow     = ''
	document.body.style.paddingRight = ''
	document.body.style.touchAction  = ''
	window.scrollTo(0, _lockedY || 0)
}

// 1度だけ呼ぶ
export function wireOffcanvasBodyLock () {
	document.addEventListener('shown.bs.offcanvas', lockBody)
	document.addEventListener('hidden.bs.offcanvas', unlockBody)
}

function _getEl(target) {
	// 文字列なら id or セレクタに対応
	if (typeof target === 'string') {
		const id = target.startsWith('#') ? target.slice(1) : target
		return document.getElementById(id) || document.querySelector(target)
	}
	return target
}

export function openSidebar (target = '#castSidebar', opts = {}) {
	const el = _getEl(target)
	if (!el) { console.warn('[offcanvas] target not found:', target); return }
	const oc = Offcanvas.getOrCreateInstance(el, {
		backdrop: true, scroll: false, keyboard: true, ...opts
	})
	oc.show()
}

export function closeSidebar (target = '#castSidebar') {
	const el = _getEl(target)
	if (!el) return
	Offcanvas.getInstance(el)?.hide()
}

/** サイドバーを閉じてから callback を実行 */
export function closeSidebarThen (cb = () => {}, target = '#castSidebar') {
	const el = _getEl(target)
	if (!el) return cb()
	const oc = Offcanvas.getInstance(el)
	if (!oc || !oc._isShown) return cb()
	const onHidden = () => { el.removeEventListener('hidden.bs.offcanvas', onHidden); cb() }
	el.addEventListener('hidden.bs.offcanvas', onHidden)
	oc.hide()
}
