// src/stores/useCastEvents.js
import { ref } from 'vue'
import { fetchBills } from '@/api'

/**
 * キャスト用イベント購読（軽ポーリングのみ）
 * @param {{cast_id:number}} me       /api/me のオブジェクト想定
 * @param {(events:any[])=>void} onChange  受信時コールバック（[{type:'selforder_count',count}]）
 */
export function useCastEvents(me, onChange){
  const running = ref(false)
  let timer = null
  const V_MS = 10_000, H_MS = 30_000    // 画面可視/不可視の間隔
  const last = { count: -1 }

  const visible = () => document.visibilityState === 'visible'

  async function tick(){
    if (!running.value) return
    try{
      const meId = Number(me?.cast_id)
      if (!Number.isFinite(meId)) return schedule()

      // 背景ポーリングのため、ローディング表示しない
      const data  = await fetchBills({ limit: 100 }, { meta: { silent: true } })
      const bills = Array.isArray(data.results) ? data.results : data
      const count = bills.filter(b => (b.stays || []).some(s =>
        Number(s?.cast?.id ?? s?.cast_id) === meId &&
        s.is_honshimei === true &&
        !s.left_at
      )).length

      if (count !== last.count){
        last.count = count
        onChange?.([{ type:'selforder_count', count }])
      }
    }catch(_e){
      /* 無視して次回 */
    }finally{
      schedule()
    }
  }

  function schedule(){
    if (!running.value) return
    timer = setTimeout(tick, visible() ? V_MS : H_MS)
  }

  function start(){
    if (running.value || !me?.cast_id) return
    running.value = true
    document.addEventListener('visibilitychange', visHandler)
    tick()
  }

  function stop(){
    running.value = false
    if (timer){ clearTimeout(timer); timer = null }
    document.removeEventListener('visibilitychange', visHandler)
  }

  function visHandler(){
    if (!running.value) return
    if (timer){ clearTimeout(timer); timer = null }
    tick()
  }

  return { start, stop }
}
