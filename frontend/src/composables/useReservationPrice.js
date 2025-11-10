// Vue 3  /  script-setup でも普通の Options API でも共通で使えます
import { computed, unref } from 'vue'

/**
 * 引数に渡された “数字 or 配列(Ref 含む)” から合計額を取り出すユーティリティ
 * @param {number|Array|import('vue').Ref<number|Array>} input
 * @returns {number}
 */
function toSum (input) {
  const value = unref(input)               // Ref なら中身を取り出す

  // 数字ならそのまま
  if (typeof value === 'number') return value || 0

  // 配列じゃなければ 0
  if (!Array.isArray(value)) return 0

  // [{amount: …}] の合計
  return value.reduce((t, item) => t + (+item.amount || 0), 0)
}

/**
 * 予約の金額（粗利／経費差引後）をまとめて算出する composable
 *
 * @param {object} args
 * @param {number|Ref<number>} args.cast      - コース＋キャスト料金
 * @param {number|Ref<number>} args.option    - オプション合計
 * @param {number|Ref<number>} args.extend    - 延長料金
 * @param {Array|Ref<Array>}   args.revenues  - 追加売上 [{label, amount}]
 * @param {Array|Ref<Array>}   args.expenses  - 経費       [{label, amount}]
 *
 * @return {{ gross: import('vue').ComputedRef<number>,
 *            net  : import('vue').ComputedRef<number> }}
 */
export function useReservationPrice ({
  cast,
  option,
  extend,
  revenues,
  expenses
}) {
  /* --- 追加売上＆経費の合計 --- */
  const revenueSum = computed(() => toSum(revenues))
  const expenseSum = computed(() => toSum(expenses))

  /* --- 経費控除前（粗利）の合計 --- */
  const gross = computed(() =>
      (+unref(cast)   || 0)
    + (+unref(option) || 0)
    + (+unref(extend) || 0)
    + revenueSum.value
  )

  /* --- 経費差し引き後の最終見積 --- */
  const net = computed(() => gross.value - expenseSum.value)

  return { gross, net }
}
