// src/utils/money.js
const YEN_FMT = new Intl.NumberFormat('ja-JP', { style:'currency', currency:'JPY', minimumFractionDigits:0 })
export function yen(value){
  const n = Number(value)
  return Number.isFinite(n) ? YEN_FMT.format(n) : '–'
}
