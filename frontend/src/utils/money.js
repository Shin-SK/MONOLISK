// src/utils/money.js
export function yen(value) {
  if (value == null || isNaN(value)) return '–';   // － 表示など
  return new Intl.NumberFormat('ja-JP', {
    style: 'currency',
    currency: 'JPY',
    minimumFractionDigits: 0
  }).format(value);
}