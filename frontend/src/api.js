// src/api.js
import axios from 'axios'
import qs        from 'qs'
import { useLoading } from '@/stores/useLoading'   // ★追加
import NProgress from 'nprogress'                  // ★追加
import 'nprogress/nprogress.css'
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/',
})
import dayjs from 'dayjs'

const TOKEN_KEY='token', STORE_KEY='store_id'
const getToken   = () => localStorage.getItem(TOKEN_KEY)
const getStoreId = () => localStorage.getItem(STORE_KEY)
const clearAuth  = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(STORE_KEY)
  delete api.defaults.headers.common.Authorization   // ← 追加
}

console.warn('__MARK__ api.js loaded', new Date().toISOString())
/* ---------------------------------------- */
/* 共通レスポンスインターセプタ & パーサ          */
/* ---------------------------------------- */

function parseApiError(err){
	if(!err.response) return 'ネットワークエラー'

	const data = err.response.data
	if(typeof data === 'string') return data
	if(data.detail) return data.detail
	if(typeof data === 'object'){
		return Object.entries(data)
			.map(([k,v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
			.join('\n')
	}
	return '不明なエラー'
}

/* ------------------------------------------------------------------ */
/* interceptor: “ログイン系 URL には token を付けない”                    */
/* ------------------------------------------------------------------ */
const SKIP_AUTH = [
  'dj-rest-auth/login/',
  'dj-rest-auth/registration/',
  'dj-rest-auth/password/reset/',
]

// request 側（401処理は置かない）
api.interceptors.request.use(cfg => {
  const loading = useLoading()
  const silent = cfg.headers?.['X-Silent'] === '1' || cfg.meta?.silent
  if (!silent) { loading.start(); NProgress.start() }
  if (cfg.data instanceof FormData) delete cfg.headers['Content-Type']

  if (!SKIP_AUTH.some(p => cfg.url.includes(p))) {
    const t = getToken()
    if (t) cfg.headers.Authorization = `Token ${t}`
  }

  const storeId = getStoreId()
  if (storeId) {
    if ((cfg.method ?? 'get').toLowerCase() === 'get') {
      cfg.params ??= {}
      cfg.params.store_id ??= storeId
    } else if (cfg.data && typeof cfg.data === 'object' && !Array.isArray(cfg.data)) {
      cfg.data.store_id ??= storeId
    }
  }
  return cfg
})

// response 側（ここで401を拾ってクリア＆リダイレクト）
api.interceptors.response.use(
  res => {
    const loading = useLoading()
    const silent = res.config?.headers?.['X-Silent'] === '1' || res.config?.meta?.silent
    if (!silent) { loading.end(); NProgress.done() }
    return res
  },
  err => {
    const loading = useLoading()
    const silent = err.config?.headers?.['X-Silent'] === '1' || err.config?.meta?.silent
    if (!silent) { loading.end(); NProgress.done() }
    if (err.response?.status === 401) {
      clearAuth()
      // ログイン系URL以外でだけリダイレクト
      if (!SKIP_AUTH.some(p => err.config?.url?.includes(p)) && location.pathname !== '/login') {
        const next = encodeURIComponent(location.pathname + location.search)
        location.assign(`/login?next=${next}`)
      }
    }
    return Promise.reject(err)
  }
)



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
  // 数字でも {table_id: n} でもOKにする保険
  const payload = typeof arg === 'number'
    ? { table_id: arg }
    : (arg?.table_id ? arg : { table_id: arg?.table });
  return api.post('billing/bills/', payload).then(r => r.data)
}

 export const deleteBill = id =>
   api.delete(`billing/bills/${id}/`)
 
export const addBillItem  = (id,p)  => 
  api.post(`billing/bills/${id}/items/`, p).then(r => r.data)

 export const closeBill = (id, payload = {}) =>
   api.post(`billing/bills/${id}/close/`, payload).then(r => r.data)
 
export const fetchMasters = storeId => api.get('billing/item-masters/', { params:{store:storeId} }).then(r=>r.data)

export const fetchCasts = storeId =>
  api.get('billing/casts/', { params:{store:storeId} })
     .then(r => r.data.results ?? r.data)

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

export const fetchTables = storeId =>
  api.get('billing/tables/', { params:{ store:storeId } }).then(r=>r.data)

export const deleteBillItem = (billId, itemId) =>
  api.delete(`billing/bills/${billId}/items/${itemId}/`)

export const getStore  = id => api.get(`billing/stores/${id}/`).then(r => r.data)


//PL

export async function getBillDailyPL(date, storeId) {
  const params = { date };
  if (storeId) params.store_id = storeId;
  const { data } = await api.get('billing/pl/daily/', { params });
  return {
    sales_cash: 0,
    sales_card: 0,
    sales_total: 0,
    cast_labor: 0,
    driver_labor: 0,
    custom_expense: 0,
    gross_profit: 0,
    ...data,
  };
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

export const fetchStaffShifts  = (params = {}) =>
  api.get('billing/staff-shift-plans/', { params }).then(r => r.data)

 export const createStaffShift = payload =>
  api.post('billing/staff-shift-plans/', {
    store_id: getStoreId(),   // ← ヘッダに持っている自店 ID を注入
    ...payload,
  }).then(r => r.data)

export const patchStaffShift   = (id, p) =>
  api.patch(`billing/staff-shift-plans/${id}/`, p).then(r => r.data)

export const deleteStaffShift  = id =>
  api.delete(`billing/staff-shift-plans/${id}/`)


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
  const sid = getStoreId();
  if (payload instanceof FormData) {
    // create では cover_clear は送らない
    payload.delete?.('cover_clear');
    return api.post('billing/store-notices/', payload, {
      params: sid ? { store_id: sid } : {},
    }).then(r => r.data);
  }
  const p = { ...payload };
  delete p.store;       // 送らない
  delete p.cover_clear; // 送らない
  return api.post('billing/store-notices/', p).then(r => r.data);
};

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
