/**
 * src/utils/businessTime.js
 * 営業時間ロジック（日跨ぎ対応）
 * 
 * 日跨ぎ営業（例 20:00-翌03:00）を扱う際の共通ユーティリティ。
 * バックエンドは hour=0..23 で返すため、フロントで拡張時刻に変換して集計。
 */

/**
 * store オブジェクトから営業時間をパース
 * @param {Object} store - Store モデル（business_hours_display を含む）
 * @returns {Object} { openHour: int, closeHour: int }
 * @example
 *   parseBusinessHours(store) // { openHour: 20, closeHour: 27 }
 */
export function parseBusinessHours(store) {
  if (!store?.business_hours_display) {
    return { openHour: 9, closeHour: 23 }
  }

  const match = store.business_hours_display.match(
    /(\d{2}):(\d{2})-(?:翌)?(\d{2}):(\d{2})/
  )
  if (!match) {
    return { openHour: 9, closeHour: 23 }
  }

  const openH = parseInt(match[1], 10)
  let closeH = parseInt(match[3], 10)

  if (store.business_hours_display.includes('翌')) {
    closeH += 24
  }

  return { openHour: openH, closeHour: closeH }
}

/**
 * バックエンドの hour (0..23) を、営業開始基準の拡張時刻に変換
 * 
 * 例1: open=20 のとき
 *   - hour=0 (00:00) -> 24 (翌00:00)
 *   - hour=3 (03:00) -> 27 (翌03:00)
 *   - hour=20 (20:00) -> 20 (営業開始)
 * 
 * 例2: open=9 のとき
 *   - hour=9 (09:00) -> 9 (営業開始)
 *   - hour=12 (12:00) -> 12
 * 
 * @param {number} hour - バックエンドから返された hour (0..23)
 * @param {number} openHour - その店舗の営業開始時刻 (0..23)
 * @returns {number} 拡張時刻 (openHour ~ openHour+23)
 */
export function hourToExtended(hour, openHour) {
  // openHour 以上なら、そのまま return
  if (hour >= openHour) {
    return hour
  }
  // openHour 未満なら、翌日扱い（+24）
  return hour + 24
}

/**
 * 拡張時刻を表示ラベルに変換
 * @param {number} extHour - 拡張時刻 (例: 20, 24, 27)
 * @returns {string} ラベル (例: "20:00", "翌00:00", "翌03:00")
 */
export function extendedToLabel(extHour) {
  const normalizedHour = extHour % 24
  const hh = String(normalizedHour).padStart(2, '0')
  
  if (extHour >= 24) {
    return `翌${hh}:00`
  }
  return `${hh}:00`
}

/**
 * startExt ～ endExt の範囲で、1時間刻みの拡張時刻配列を生成
 * @param {number} startExt - 開始拡張時刻
 * @param {number} endExt - 終了拡張時刻（この時刻は含まない）
 * @returns {number[]} 拡張時刻の配列
 * @example
 *   buildHourRange(20, 27) // [20, 21, 22, 23, 24, 25, 26]
 *   buildHourRange(19, 29) // [19, 20, ..., 28]
 */
export function buildHourRange(startExt, endExt) {
  const range = []
  for (let h = startExt; h < endExt; h++) {
    range.push(h)
  }
  return range
}

/**
 * 複数店舗の営業時間から、グラフ表示範囲を計算
 * 
 * @param {Array} stores - Store オブジェクト配列（各要素は business_hours_display を持つ）
 * @returns {Object} {
 *   openingHour: number,  // 選択店舗の最小開始時刻（例: 20）
 *   closingHour: number,  // 選択店舗の最大終了時刻。日跨ぎの場合は 24+ (例: 27)
 *   hours: number[]       // openingHour ... closingHour-1 の配列（例: [20,21,22,23,24,25,26]）
 * }
 * @example
 *   // 店舗A: 20:00-27:00, 店舗B: 19:00-29:00
 *   displayRangeFromStores([storeA, storeB])
 *   // -> { openingHour: 19, closingHour: 29, hours: [19,20,...,28] }
 */
export function displayRangeFromStores(stores) {
  if (!Array.isArray(stores) || stores.length === 0) {
    return {
      openingHour: 9,
      closingHour: 23,
      hours: buildHourRange(9, 23)
    }
  }

  let minOpen = 24
  let maxClose = 0

  stores.forEach(store => {
    const { openHour, closeHour } = parseBusinessHours(store)
    minOpen = Math.min(minOpen, openHour)
    maxClose = Math.max(maxClose, closeHour)
  })

  return {
    openingHour: minOpen,
    closingHour: maxClose,
    hours: buildHourRange(minOpen, maxClose)
  }
}

/**
 * 複数店舗の営業時間から、グラフ表示範囲を決定（レガシー）
 * @param {Array} stores - Store オブジェクト配列
 * @returns {Object} { minExt: number, maxExt: number }
 */
export function getGraphRange(stores) {
  const range = displayRangeFromStores(stores)
  return { minExt: range.openingHour, maxExt: range.closingHour }
}

export default {
  parseBusinessHours,
  hourToExtended,
  extendedToLabel,
  buildHourRange,
  displayRangeFromStores,
  getGraphRange
}
