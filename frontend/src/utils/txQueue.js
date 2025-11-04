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
  if (i >= 0) store.list[i].id = realId
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
    return { realId: res.id }
  },
  async patchBill(p){ await patchBill(p.id, p.payload) },               // {id, payload}
  async updateBillCustomers(p){ await updateBillCustomers(p.id, p.customer_ids) },
  async updateBillCasts(p){
    await updateBillCasts(p.billId, {
      nomIds: p.nomIds || [], inIds: p.inIds || [], freeIds: p.freeIds || [], dohanIds: p.dohanIds || []
    })
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

        // create → tempId を realId に差し替える
        if (task.kind === 'createBill' && res?.realId && task.payload?.tempId){
          replaceTempIdEverywhere(task.payload.tempId, res.realId)
          replaceTempIdInStore(task.payload.tempId, res.realId)
        }

        queue.splice(idx,1); save(queue)
      }catch(e){
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
