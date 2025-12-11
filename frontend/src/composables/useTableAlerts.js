import { computed, ref } from 'vue'
import dayjs from 'dayjs'

/**
 * テーブルアラート検知composable
 * 残り時間が10分以下のテーブルを抽出し、アラート状態を管理
 */
export function useTableAlerts(billsRef) {
  const tick = ref(Date.now())

  // 1分ごとに更新
  const tickInterval = setInterval(() => {
    tick.value = Date.now()
  }, 60_000)

  // 残り時間を計算（分単位）
  function calcRemainMin(bill) {
    if (!bill || !bill.opened_at) return null
    const elapsed = dayjs().diff(dayjs(bill.opened_at), 'minute')
    const limit = bill.round_min || 60
    return Math.max(limit - elapsed, 0)
  }

  // アラート対象の伝票（残り10分以下、かつ未クローズ）
  const urgentBills = computed(() => {
    const bills = billsRef.value || []
    return bills.filter(b => {
      if (b.closed_at) return false
      const remain = calcRemainMin(b)
      return remain !== null && remain <= 10
    })
  })

  // アラートがあるか
  const hasUrgent = computed(() => urgentBills.value.length > 0)

  // アラート件数
  const urgentCount = computed(() => urgentBills.value.length)

  // 特定の伝票に対するアラート状態
  function getAlertState(bill) {
    if (!bill || bill.closed_at) return null
    const remain = calcRemainMin(bill)
    if (remain === null) return null
    if (remain <= 0) {
      return {
        isAlert: true,
        message: '退席時刻を過ぎています',
        severity: 'danger'
      }
    }
    if (remain <= 10) {
      return {
        isAlert: true,
        message: `残り時間${remain}分です`,
        severity: 'danger'
      }
    }
    return null
  }

  // cleanup
  const cleanup = () => clearInterval(tickInterval)

  return {
    urgentBills,
    hasUrgent,
    urgentCount,
    calcRemainMin,
    getAlertState,
    cleanup,
    tick // reactive外での参照用
  }
}
