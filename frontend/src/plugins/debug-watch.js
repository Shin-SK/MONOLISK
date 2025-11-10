// debug-watch.js（どこかに置く。import して実行するだけ）
import { watch } from 'vue'

/**
 * 任意の getter を監視して型と値を出力する
 * @param {String} label - コンソールに付けるラベル
 * @param {Function} getter - 監視したい reactive 値を返す関数
 */
export function debugWatch(label, getter) {
  watch(getter, (nv, ov) => {
    console.log(
      `%c[${label}]`,
      'color:#0a0;font-weight:bold',
      {
        before: ov,
        after : nv,
        typeof_after:
          Array.isArray(nv)
            ? nv.map(v => typeof v)
            : typeof nv
      }
    )
  }, { deep: true, immediate: true })
}
