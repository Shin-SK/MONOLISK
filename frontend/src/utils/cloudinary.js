// src/utils/cloudinary.js
const isCloudinary = (u) => /res\.cloudinary\.com/.test(u)

// /upload/〜/v1234/ の「〜」(変換) を剥がす
const stripTransforms = (src) =>
	src.replace(/\/upload\/(?:[^/]+\/)*(v\d+\/)/, '/upload/$1')

const buildTransform = (w, h, opt={}) => {
	const q   = opt.quality || 'auto:good'
	const fmt = opt.format  || 'auto'
	const dpr = opt.dpr     || 'auto'
	const crop= opt.crop    || 'fill'
	const g   = opt.gravity || 'auto'
	return `f_${fmt},q_${q},dpr_${dpr},c_${crop},g_${g},w_${Math.round(w)},h_${Math.round(h)}`
}

export function avatarUrl(src, w, h, opt={}){
	if (!src) return ''
	if (!isCloudinary(src)) return src
	const base = stripTransforms(src)
	const t = buildTransform(w, h, opt)
	return base.replace('/upload/', `/upload/${t}/`)
}

export function avatarSrcset(src, base){
	if (!src) return ''
	const w1 = base, w2 = base*2, w3 = base*3
	return [
		`${avatarUrl(src, w1, w1)} 1x`,
		`${avatarUrl(src, w2, w2)} 2x`,
		`${avatarUrl(src, w3, w3)} 3x`,
	].join(', ')
}
