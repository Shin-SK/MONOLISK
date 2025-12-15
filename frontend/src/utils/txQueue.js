// frontend/src/utils/txQueue.js
// 楽観更新用の超軽量送信キュー（localStorage 永続）
// 裏で順送 → 完了後に最新Billで和解（reconcile）

import {
  fetchBill, createBill, patchBill, addBillItem,
  updateBillCustomers, updateBillCasts, updateBillTable,
  deleteBill, closeBill
} from '@/api'
import { useBills } from '@/stores/useBills'

const LS_KEY = 'txqueue:v1'
const sleep = (ms)=> new Promise(r=>setTimeout(r, ms))

function load(){ try{ return JSON.parse(localStorage.getItem(LS_KEY) || '[]') }catch{ return [] } }
function save(q){ localStorage.setItem(LS_KEY, JSON.stringify(q)) }

let queue = load()
let running = false

function upsertBillInStore(b){
  const store = useBills()
  const i = store.list.findIndex(x => Number(x.id) === Number(b.id))
  if (i >= 0) store.list[i] = b
  else store.list.unshift(b)
}
function replaceTempIdInStore(tempId, realId){
  const store = useBills()
  const i = store.list.findIndex(x => Number(x.id) === Number(tempId))
  if (i >= 0) {
    // ★ IDを置き換えた上で、古いtempIDエントリを削除（重複防止）
    store.list[i].id = realId
    // もし既にrealIdを持つ別Billがあれば古いものを優先削除
    const j = store.list.findIndex((x, idx) => idx !== i && Number(x.id) === Number(realId))
    if (j >= 0) store.list.splice(j, 1)
  }
}

async function deleteBillRunner(p){ // {id}
  // DELETE はキャッシュ対象外だが、明示で
  await deleteBill(p.id) // api側でcache:falseにしてもOK
}

const runners = {
  async createBill(p){ // {tempId, table_id, memo, opened_at, expected_out}
    const res = await createBill({
      table_id: p.table_id, opened_at: p.opened_at, expected_out: p.expected_out, memo: p.memo
    })
    try { console.log('[diag txQueue:createBill]', { tempId: p.tempId, realId: res.id }) } catch(e){ /* noop */ }
    return { realId: res.id }
  },
  async patchBill(p){
    // opened_at/expected_out を送らない PATCH で現在時刻にリセットされるのを防ぐ
    const store = useBills()
    const b = store.list.find(x => Number(x.id) === Number(p.id)) || {}
    const payload = { ...p.payload }
    if (payload.opened_at === undefined)    payload.opened_at = b.opened_at ?? null
    if (payload.expected_out === undefined) payload.expected_out = b.expected_out ?? null
    await patchBill(p.id, payload)
  },               // {id, payload}
  async updateBillCustomers(p){ await updateBillCustomers(p.id, p.customer_ids) },
  async updateBillCasts(p){
    const payload = { nomIds: p.nomIds || [], inIds: p.inIds || [], freeIds: p.freeIds || [], dohanIds: p.dohanIds || [] }
    let res = null
    try {
      res = await updateBillCasts(p.billId, payload)
      console.log('[diag txQueue:updateBillCasts:ok]', {
        billId: p.billId,
        nomIds: payload.nomIds,
        inIds: payload.inIds,
        freeIds: payload.freeIds,
        dohanIds: payload.dohanIds,
        stays: (res?.stays||[]).filter(s=>!s.left_at).map(s => ({ cast: s.cast.id, stay_type: s.stay_type })),
        nominated_casts: (res?.nominated_casts||[]).map(c=>c.id||c),
      })
      // 即時ストア反映（reconcile 待ちで上書きされる前に）
      if (res) {
        try { upsertBillInStore(res) } catch(e){ console.warn('[diag txQueue:updateBillCasts:upsertFail]', e?.message) }
      }
    } catch(err){
      console.error('[diag txQueue:updateBillCasts:err]', { billId: p.billId, payload, error: err?.message })
      throw err
    }
  },
  async addBillItem(p){ await addBillItem(p.id, p.item) },              // {id, item:{ item_master, qty, served_by_cast_id? }}
  async updateBillTable(p){ await updateBillTable(p.id, p.table_id) },  // {id, table_id}
  deleteBill: deleteBillRunner,
  async closeBill(p){            // { id, payload:{ settled_total } }
    await closeBill(p.id, p.payload || {})
  },
  async reconcile(p){                                                   // {id}
    const real = await fetchBill(p.id).catch(()=>null)
    if (real) upsertBillInStore(real)
  }
}

export function startTxQueue(){
  if (running) return
  running = true
  ;(async function loop(){
    while(running){
      const now = Date.now()
      const idx = queue.findIndex(t => (t.nextAt||0) <= now)
      if (idx === -1) { await sleep(250); continue }
      const task = queue[idx]
      try{
        const fn = runners[task.kind]
        if (!fn) throw new Error(`unknown kind: ${task.kind}`)
        const res = await fn(task.payload)
        try { console.log('[diag txQueue:taskDone]', { kind: task.kind, payload: task.payload, result: res }) } catch(e){ /* noop */ }

        // create → tempId を realId に差し替える
        if (task.kind === 'createBill' && res?.realId && task.payload?.tempId){
          replaceTempIdEverywhere(task.payload.tempId, res.realId)
          replaceTempIdInStore(task.payload.tempId, res.realId)
        }

        queue.splice(idx,1); save(queue)
      }catch(e){
        try { console.warn('[diag txQueue:taskError]', { kind: task.kind, payload: task.payload, error: e?.message }) } catch(_){ /* noop */ }
        task.tries = (task.tries||0)+1
        const wait = Math.min(60000, Math.pow(2, task.tries) * 1000) // 最大60秒
        task.nextAt = Date.now() + wait
        queue[idx] = task; save(queue)
        if (!navigator.onLine) await sleep(1500)
      }
    }
  })().catch(e => { console.error('[txQueue] fatal', e); running=false })
}

export function enqueue(kind, payload){
  const t = { id:`${Date.now()}-${Math.random().toString(36).slice(2)}`, kind, payload, tries:0, nextAt:0 }
  queue.push(t); save(queue)
  if (!running) startTxQueue()
  return t.id
}

function replaceTempIdEverywhere(tempId, realId){
  queue = queue.map(t => {
    const p = t.payload || {}
    if (p.id === tempId) p.id = realId
    if (p.billId === tempId) p.billId = realId
    if (p.payload && p.payload.bill_id === tempId) p.payload.bill_id = realId
    t.payload = p
    return t
  })
  save(queue)
}
