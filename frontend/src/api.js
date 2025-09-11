// src/api.js
import axios from 'axios'
import 'nprogress/nprogress.css'
import { wireInterceptors } from '@/api/interceptors'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/',
})
import dayjs from 'dayjs'

console.warn('__MARK__ api.js loaded', new Date().toISOString())


/* ------------------------------------------------------------------ */
/* interceptor: “ログイン系 URL には token を付けない”                    */
/* ------------------------------------------------------------------ */

// インターセプタを装着（/api/me はStore非依存 = デフォのskipStore['me/']のみ）
wireInterceptors(api)

/* ------------------------------------------------------------------ */
/* 認証 API                                                            */
/* ------------------------------------------------------------------ */

/* 認証系はauth.jsで統一 */


/* ------------------------------------------------------------------ */
/* Bills キャバクラ版への移植版。現在のメイン
/* ------------------------------------------------------------------ */


// すでに baseURL が `/api/` なので “billing/...” を付ける

export const fetchBills   = (params={}) =>
  api.get('billing/bills/', { params }).then(r=>r.data)

export const fetchBill    = id      => api.get(`billing/bills/${id}/`).then(r=>r.data)
// src/api.js
export const createBill = (arg) => {
	const payload = typeof arg === 'number'
		? { table_id: arg }
		: (arg?.table_id ? arg : { table_id: arg?.table })
	return api.post('billing/bills/', payload).then(r => r.data)
}

 export const deleteBill = id =>
   api.delete(`billing/bills/${id}/`)
 
export const addBillItem  = (id,p)  => 
  api.post(`billing/bills/${id}/items/`, p).then(r => r.data)

 export const closeBill = (id, payload = {}) =>
   api.post(`billing/bills/${id}/close/`, payload).then(r => r.data)
 
export const fetchMasters = () => api.get('billing/item-masters/').then(r=>r.data)

export const fetchCasts   = () => api.get('billing/casts/').then(r => r.data.results ?? r.data)

/**
 * 指名／場内／フリーの配列をまとめて PATCH
 *   nomIds  = 本指名キャスト ID[]
 *   inIds   = 場内キャスト ID[]
 *   freeIds = フリー在席キャスト ID[]
 */
export const updateBillCasts = (
  billId,
  { nomIds = [], inIds = [], freeIds = [] }
) => {
  return api
    .patch(`billing/bills/${billId}/`, {
      nominated_casts : nomIds,   // 本指名
      inhouse_casts_w : inIds,    // 場内
      free_ids        : freeIds,  // フリー
    })
    .then(res => res.data)        // 成功時は data だけ返す
    .catch(err => {               // ここで拾っておけば呼び出し側で表示できる
      throw err
    })
}

export const setInhouseStatus = updateBillCasts; //ローダー用にエイリアス

export const fetchTables  = () => api.get('billing/tables/').then(r=>r.data)

export const deleteBillItem = (billId, itemId) =>
  api.delete(`billing/bills/${billId}/items/${itemId}/`)

export const getStore  = id => api.get(`billing/stores/${id}/`).then(r => r.data)


//PL

export async function getBillDailyPL(date) {
	const { data } = await api.get('billing/pl/daily/', { params: { date } })
	return { sales_cash:0, sales_card:0, sales_total:0, cast_labor:0, driver_labor:0, custom_expense:0, gross_profit:0, ...data }
}


export const getBillMonthlyPL = (monthStr) => {
  const [year, month] = monthStr.split('-').map(Number)
  return api.get('billing/pl/monthly/', { params: { year, month } })
    .then(r => {
      const days = (r.data.days ?? []).map(d => ({
        sales_cash: 0, sales_card: 0, sales_total: 0,
        cast_labor: 0, driver_labor: 0, custom_expense: 0, gross_profit: 0,
        ...d,
      }))
      const mt = {
        sales_cash: 0, sales_card: 0, sales_total: 0,
        cast_labor: 0, driver_labor: 0, custom_expense: 0, gross_profit: 0,
        ...r.data.monthly_total,
      }
      return { days, monthly_total: mt }
    })
}


export const getBillYearlyPL = (year) =>
  api.get('billing/pl/yearly/', { params: { year } })
    .then(r => {
      const d = r.data ?? {}
      // 年間トータルは d.totals に入ってくる想定（営業日対応版）
      const totals = {
        sales_cash       : d.totals?.sales_cash       ?? 0,
        sales_card       : d.totals?.sales_card       ?? 0,
        sales_total      : d.totals?.sales_total      ?? 0,
        guest_count      : d.totals?.guest_count      ?? 0,
        avg_spend        : d.totals?.avg_spend        ?? 0,
        labor_cost       : d.totals?.labor_cost       ?? 0,
        operating_profit : d.totals?.operating_profit ?? 0,
      }
      // months は {month, totals:{...}} の配列
      const months = (Array.isArray(d.months) ? d.months : []).map(m => ({
        month: m.month,
        totals: {
          sales_cash       : m.totals?.sales_cash       ?? 0,
          sales_card       : m.totals?.sales_card       ?? 0,
          sales_total      : m.totals?.sales_total      ?? 0,
          guest_count      : m.totals?.guest_count      ?? 0,
          avg_spend        : m.totals?.avg_spend        ?? 0,
          labor_cost       : m.totals?.labor_cost       ?? 0,
          operating_profit : m.totals?.operating_profit ?? 0,
          // ほか（cast_labor 等）は来てなくても OK。Vue 側 blankTotals で 0 埋め
        }
      }))
      return { year: d.year, totals, months }
    })


// キャスト系

export const getBillingStores = () =>
	api.get('billing/stores/').then(r => r.data)
export const getStores = getBillingStores

export const getBillingCasts = (params = {}) =>
	api.get('billing/casts/', { params }).then(r => r.data)


/* ---------- キャスト売上 ---------- */
export const fetchCastSalesSummary = (params = {}) =>
  api.get('billing/cast-sales/', { params }).then(r => r.data)


export const fetchCastSalesDetail = (castId, params = {}) =>
  api.get('billing/cast-payouts/', {
    params: { cast: castId, ...params }
  }).then(r => r.data)

export const fetchCastItemDetails = (castId, params = {}) =>
  api.get('billing/cast-items/', {
    params: { cast: castId, ...params }
  }).then(r => r.data)

/**
 * 一覧取得
 *   params: { cast, date, ordering, ... }
 */
export const fetchCastShifts = (params = {}, { silent=false } = {}) =>
  api.get('billing/cast-shifts/', {
    params,
    ...(silent ? { meta: { silent: true } } : {})
  }).then(r => r.data)

/**
 * 予定＋実績の新規作成
 *   payload: { cast_id, store_id, plan_start, plan_end, clock_in, clock_out }
 */
export const createCastShift = payload =>
    api.post('billing/cast-shifts/', payload).then(r => r.data)

/**
 * 更新（汎用）
 *   id:        shift 行 ID
 *   payload:   任意フィールドを部分更新
 */
export const patchCastShift = (id, payload) =>
    api.patch(`billing/cast-shifts/${id}/`, payload).then(r => r.data)

/**
 * 削除
 */
export const deleteCastShift = id =>
    api.delete(`billing/cast-shifts/${id}/`)

/* --- 便利ラッパ --- */

/** 出勤打刻 (clock_in を現在時刻でセット) */
export const castCheckIn = (id, at = dayjs().toISOString()) =>
    patchCastShift(id, { clock_in: at })

/** 退勤打刻 (clock_out を現在時刻でセット) */
export const castCheckOut = (id, at = dayjs().toISOString()) =>
    patchCastShift(id, { clock_out: at })

/* ---------- Cast シフト履歴 ---------- */
export const fetchCastShiftHistory = (castId, params = {}) =>
  api.get('billing/cast-shifts/', {
    params: { cast: castId, ordering: '-clock_in', ...params },
  }).then(r => r.data)

export const updateCastShift = (id, payload) =>
  api.patch(`billing/cast-shifts/${id}/`, payload).then(r => r.data)


/* ★NEW:  出勤打刻だけクリア（予定は残す） */
export const clearCastAttendance = id =>
  api.patch(`billing/cast-shifts/${id}/`, {
    clock_in : null,
    clock_out: null,
  }).then(r => r.data)  


export const fetchCastDailySummaries = (params = {}) =>
  api.get('billing/cast-daily-summaries/', { params })
     .then(r => r.data);


/* ---------- Cast ランキング ---------- */
/**
 * Top‑10 ランキング
 *   params: { from:'YYYY-MM-DD', to:'YYYY-MM-DD' } 省略時＝当月
 */
export const fetchCastRankings = (params = {}) =>
  api.get('billing/cast-ranking/', { params }).then(r => r.data)


/* ---------- Cast 詳細 & 店舗お知らせ ---------- */

/** キャスト 1 名の詳細（stage_name, avatar_url など） */
export const fetchCastMypage = id =>
  api.get(`billing/casts/${id}/`).then(r => r.data)

export const fetchStoreNotices = (params = {}) =>
  api.get('billing/store-notices/', {
    params: {
      status: 'published',                           // 公開のみ
      ordering: '-pinned,-publish_at,-created_at',   // 並び
      limit: 20,                                     // 件数（必要に応じて）
      ...params,
    },
  }).then(r => r.data?.results ?? r.data ?? []);

// ─────────────────────────────────────────────
//  Staff APIs  ★ここから下を api.js のどこかに追記
// ─────────────────────────────────────────────

/**
 * 今日のシフト予定（勤務表）
 *   params: { date:'YYYY-MM-DD', /* store_id はヘッダに自動付加 *\/ }
 *
 * 例）getStaffShiftPlans({ date:'2025-08-04' })
 */
export const getStaffShiftPlans = (params = {}) =>
  api.get('billing/staff-shift-plans/', { params })
     .then(r => r.data)



/* ---------- Staff & StaffShift ---------- */
// スタッフ一覧
export const fetchStaffs = (params = {}) =>
  api.get('billing/staffs/', { params })
     .then(r => r.data.results ?? r.data)   // ページネーション両対応


/* ---------- Staff CRUD ---------- */
export const fetchStaff = id =>
  api.get(`billing/staffs/${id}/`).then(r => r.data)

export const createStaff = payload =>
  api.post('billing/staffs/', payload).then(r => r.data)

export const updateStaff = (id, payload) =>
  api.put(`billing/staffs/${id}/`, payload).then(r => r.data)

export const deleteStaff = id =>
  api.delete(`billing/staffs/${id}/`)

const STAFF_SHIFT_ENDPOINT = 'billing/staff-shifts/';
export const fetchStaffShifts  = (params = {}) =>
  api.get(STAFF_SHIFT_ENDPOINT, { params }).then(r => r.data)
export const createStaffShift = (payload) =>
  api.post(STAFF_SHIFT_ENDPOINT, payload).then(r => r.data)
export const patchStaffShift   = (id, p) =>
  api.patch(`${STAFF_SHIFT_ENDPOINT}${id}/`, p).then(r => r.data)
export const deleteStaffShift  = (id) =>
  api.delete(`${STAFF_SHIFT_ENDPOINT}${id}/`)

export const staffCheckIn  = (shiftId, at = dayjs().toISOString()) =>
  patchStaffShift(shiftId, { clock_in: at })

export const staffCheckOut = (shiftId, at = dayjs().toISOString()) =>
  patchStaffShift(shiftId, { clock_out: at })



// ──────────── Bills patch 共通 ────────────
export const patchBill = (id, payload) =>
  api.patch(`billing/bills/${id}/`, payload).then(r => r.data)

// --- granular wrapper ----------------------
export const updateBillTimes = (id, { opened_at, expected_out }) =>
  patchBill(id, { opened_at, expected_out })

export const updateBillCustomers = (id, customer_ids = []) =>
  patchBill(id, { customer_ids })

export const updateBillTable = (id, table_id = null) =>
  patchBill(id, { table_id })

export const toggleBillInhouse = (billId, { cast_id, inhouse }) =>
  api.post(`billing/bills/${billId}/toggle-inhouse/`, { cast_id, inhouse })
     .then(r => r.data)

export const patchBillItem = (billId, itemId, payload) =>
  api.patch(`billing/bills/${billId}/items/${itemId}/`, payload).then(r => r.data)

export const patchBillItemQty = (billId, itemId, qty) =>
  patchBillItem(billId, itemId, { qty })

// ──────────── 顧客 ────────────
export const fetchCustomer = id =>
  api.get(`billing/customers/${id}/`).then(r => r.data)

export const fetchCustomers = (params = {}) =>
  api.get('billing/customers/', { params }).then(r => r.data)



/* ---------- Store Notices (店舗ニュース) ---------- */
// 一覧（管理側・公開側どっちでも使える）
 export const listStoreNotices = async (params = {}) => {
   const { data } = await api.get('billing/store-notices/', { params })
   // ページネーション有無／items系 どれでも配列化して返す
   if (Array.isArray(data?.results)) return data.results
   if (Array.isArray(data?.items))   return data.items
   if (Array.isArray(data))          return data
   return [] // どれでもなければ空配列
 }

// 1件取得
export const getStoreNotice = (id) =>
  api.get(`billing/store-notices/${_nid(id)}/`).then(r => r.data)


export const createStoreNotice = (payload) => {
	if (payload instanceof FormData) {
		payload.delete?.('cover_clear')
		return api.post('billing/store-notices/', payload).then(r => r.data)
	}
	const p = { ...payload }
	delete p.store
	delete p.cover_clear
	return api.post('billing/store-notices/', p).then(r => r.data)
}

export const updateStoreNotice = (id, payload) => {
  const nid = (typeof id === 'object') ? (id?.id ?? id?.pk ?? id?.value) : id
  const s = String(nid)
  console.warn('[TRACE:updateStoreNotice]', {
    rawId: id, normalized: s,
    isDigits: /^\d+$/.test(s),
    isFormData: payload instanceof FormData,
    keys: payload instanceof FormData ? Array.from(payload.keys()) : Object.keys(payload || {})
  })
  console.trace('[TRACE:updateStoreNotice] call stack')
  return api.patch(`billing/store-notices/${s}/`, payload).then(r => r.data)
}

// 削除
export const deleteStoreNotice = id =>
  api.delete(`billing/store-notices/${id}/`);


function _nid(id){
  if (id == null) throw new Error('invalid id: ' + id)
  return (typeof id === 'object') ? (id.id ?? id.pk ?? id.value) : id
}

export async function longPollReady({ station, cursor, signal }) {
  const res = await api.get('/billing/order-events/', {
    params: { station, since: cursor, wait: 25 },
    timeout: 30000,
    signal
  })
  return res.data ?? { events: [], cursor, retryAfter: 800 }
}

// ───────── KDSベースURL ─────────
const KDS_BASE_RAW = import.meta.env.VITE_KDS_BASE || ''  // 例: '/api' or 'https://api.example.com/api/'
const IS_ABS = /^https?:\/\//i.test(KDS_BASE_RAW)

const norm = (d) => Array.isArray(d) ? d : (d?.results ?? d?.items ?? d ?? [])
const withStore = (cfg = {}) => {
  const sid = localStorage.getItem('store_id')
  return sid ? { ...cfg, headers:{ ...(cfg.headers||{}), 'X-Store-Id': sid, 'X-Store-ID': sid } } : cfg
}

const K = (path) => {
  const p = String(path || '').replace(/^\/+/, '')           // 先頭の / は剥がす
  if (IS_ABS) {
    const b = KDS_BASE_RAW.replace(/\/+$/, '')               // 末尾スラッシュ除去
    return `${b}/${p}`                                       // → 絶対URL
  }
  return p                                                   // → 'billing/kds/...'
}

// ───────── KDS系（全てサイレント＋30sタイムアウト）─────────
export const kds = {
  listTickets: (route) =>
    api.get(K('billing/kds/tickets/'),
      withStore({ params:{ route, station: route }, meta:{silent:true} })
    ).then(r => norm(r.data)),

  longPollTickets: (route, since_id=0, opt={}) =>
    api.get(K('billing/kds/longpoll-tickets/'),
      withStore({ params:{ route, station: route, since_id }, timeout:30000, meta:{silent:true}, ...opt })
    ).then(r => norm(r.data)),

  readyList: () =>
    api.get(K('billing/kds/ready-list/'),
      withStore({ meta:{silent:true} })
    ).then(r => norm(r.data)),

  ack:  (id) =>  api.post(K(`billing/kds/tickets/${id}/ack/`),  null, withStore({ meta:{silent:true} })).then(r=>r.data),
  ready:(id) =>  api.post(K(`billing/kds/tickets/${id}/ready/`), null, withStore({ meta:{silent:true} })).then(r=>r.data),
  take: (ticket_id, staff_id) =>
    api.post(K('billing/kds/take/'), { ticket_id, staff_id }, withStore({ meta:{silent:true} })).then(r=>r.data),

  longPollReady: (since_ms=0, opt={}) =>
    api.get(K('billing/kds/longpoll-ready/'),
      withStore({ params:{ since_ms }, timeout:30000, meta:{silent:true}, ...opt })
    ).then(r => norm(r.data)),

  staffList: (params={}) =>
    api.get(K('billing/staffs/'), { params:{ active:1, ...params }, meta:{silent:true} })
       .then(r => r.data.results ?? r.data),

  historyToday: (limit=50) =>
    api.get(K('billing/kds/taken-today/'), { params: { limit }, meta:{ silent:true } })
       .then(r => r.data),
}


// --- Owner Dashboard APIs ---

export const fetchBillItems = (params = {}) =>
  api.get('billing/cast-item-details/', { params }).then(r => r.data)


// ───────── Stores (Switcher用) ─────────
export const listMyStores = () =>
	api.get('billing/stores/my/').then(r => r.data)

/** 店舗を切り替え（ヘッダ=唯一の真実） */
export const switchStore = async (sid) => {
	const s = String(sid)
	localStorage.setItem('store_id', s)               // ヘッダはinterceptorが自動付与
	// /api/me は通常ヘッダを付けないが、ここは明示的に付けて“現在role/caps”を即取得
	const { data } = await api.get('me/', { headers: { 'X-Store-Id': s } })
	return data
}