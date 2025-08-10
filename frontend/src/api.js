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
import { getToken, getStoreId, clearAuth } from './auth'



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

api.interceptors.request.use(cfg => {
  const loading = useLoading()
  loading.start()
  NProgress.start()
  // FormData 用ヘッダ調整
  if (cfg.data instanceof FormData) delete cfg.headers['Content-Type']

  // ---- Token 付加 ---------------------------------
  if (!SKIP_AUTH.some(p => cfg.url.includes(p))) {
    const t = getToken()
    if (t) cfg.headers.Authorization = `Token ${t}`
  }

  // ---- store_id 自動付加 ---------------------------
  const storeId = getStoreId()
  if (storeId) {
    // GET → query, それ以外 → body
    if ((cfg.method ?? 'get').toLowerCase() === 'get') {
      cfg.params ??= {}
      cfg.params.store_id ??= storeId
    } else if (cfg.data && typeof cfg.data === 'object' && !Array.isArray(cfg.data)) {
      cfg.data.store_id ??= storeId
    }
  }

  return cfg
})


/* ------------------------------------------------------------------ */
/* 認証 API                                                            */
/* ------------------------------------------------------------------ */

export async function login(username, password) {
  const { data } = await api.post('dj-rest-auth/login/', {
    username,
    password,
  });

  // ▼ ここに入れる！ ──────────────────────────────
  //   - 新仕様 (token) と旧仕様 (key) の両方を許容
  //   - どちらも無いならエラーを投げる
  const token = data.key || data.token 
  if (!token) {
    throw new Error('login: token not returned');
  }

  // ③ 好きな場所に保存（例: localStorage）
  localStorage.setItem('authToken', token);

  // ④ axios 既定ヘッダをセット
  api.defaults.headers.common.Authorization = `Token ${token}`;

  return token;
}

// ⑤ ログアウト例（参考）
export async function logout() {
  try {
    await api.post('dj-rest-auth/logout/');
  } finally {
    localStorage.removeItem('authToken');
    delete api.defaults.headers.common.Authorization;
  }
}

/* ------------------------------------------------------------------ */
/* 401 ハンドリング                                                     */
/* ------------------------------------------------------------------ */
api.interceptors.response.use(
  res => {
    const loading = useLoading()
    loading.end()
    NProgress.done()
     return res
  },
  err => {
    const loading = useLoading()
    loading.end()
    NProgress.done()
    if (err.response?.status === 401) clearAuth()
    return Promise.reject(err)
  }
)


/* ------------------------------------------------------------------ */
/* Reservations いずれ整理する                                          */
/* ------------------------------------------------------------------ */

export const getReservations = (params = {}) => {
  const cleaned = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== '' && v != null)
  );
  return api.get('reservations/', { params: cleaned }).then(r => r.data);
};


export const getReservation    = id      => api.get(`reservations/${id}/`).then(r => r.data)
export const createReservation = payload => api.post('reservations/', payload).then(r => r.data)
export const updateReservation = (id, p) => api.patch(`reservations/${id}/`, p)
export const deleteReservations = (ids) =>
  axios.delete('/reservations/bulk-delete/', { data: { ids } })

export const getLatestReservation = id =>
  api.get(`customers/${id}/latest_reservation/`).then(r => r.data)

export const getCustomerAddresses = custId =>
	api.get(`customers/${custId}/addresses/`).then(r => r.data)

export const createCustomerAddress = (custId, payload) =>
	api.post(`customers/${custId}/addresses/`, payload).then(r => r.data)

/* ---------- マスター ---------- */
const simple = r => r.data
export const getStores = () => api.get('billing/stores/?simple=1').then(r => r.data)
export const getCustomers = () => api.get('customers/?simple=1').then(simple)
export const getDrivers   = () => api.get('drivers/?simple=1').then(simple)
export const getCourses   = () => api.get('courses/?simple=1').then(simple)
export const getOptions   = () => api.get('options/').then(r => r.data)

/* ---------- キャスト & 料金 ---------- */
export const getCastProfiles = (params = {}) =>
  // api.get('cast-profiles/', { params }).then(r => r.data);
  api.get('cast-profiles/', { params })
     .then(r => r.data.results ?? r.data)   // ← ここだけ
	export function getPrice(params) {
	  return api.get('pricing/', {            // ← api インスタンスで /api/pricing/
	    params,
	    paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' }),
	  }).then(r => r.data.price)
	}

/* ---------- ステータス ----------*/
export async function getReservationChoices() {
  const res = await api.options('reservations/');
  return {
   status: res.data.actions.POST.status.choices.map(c => [c.value, c.display_name])
  };
}

/* ---------- 顧客 ---------- */
export const searchCustomers = q =>
  api.get('customers/', { params: { phone: q } }).then(r => r.data)

export const createCustomer = p           => api.post('customers/', p).then(r => r.data)
export const updateCustomer = (id, p)     => api.put(`customers/${id}/`, p).then(r => r.data)
export const deleteCustomer = id          => api.delete(`customers/${id}/`)
export const getCustomer    = id          => api.get(`customers/${id}/`).then(r => r.data)

export const getReservationsByCustomer = id =>
	api.get('reservations/', {
		params:{ customer:id, ordering:'-start_at' }
	}).then(r => r.data)

/* ---------- キャストオプション ---------- */
export const getCastOptions  = castId => api.get('cast-options/', { params: { cast_profile: castId } }).then(r => r.data)
export const patchCastOption = (id, p) => api.patch(`cast-options/${id}/`, p).then(r => r.data)


/* ---------- シフト ---------- */
// 予定
export const getShiftPlans = (params={}) =>
  api.get('shift-plans/', { params }).then(r=>r.data)
export const createShiftPlan = payload =>
  api.post('shift-plans/', payload).then(r => r.data);
export const updateShiftPlan = (id, p) =>
  api.patch(`shift-plans/${id}/`, p).then(r => r.data);
export const deleteShiftPlan = id =>
  api.delete(`shift-plans/${id}/`);

// 実出勤（打刻）
export const getShiftAttendance = params =>
  api.get('shift-attendances/', { params }).then(r => r.data);
export const postCheckIn = id =>
  api.post(`shift-attendance/${id}/checkin/`).then(r => r.data);

export const createShiftAttendance = payload =>
  api.post('shift-attendances/', payload).then(r => r.data)

export const checkIn  = (id, at) =>
  api.post(`shift-attendances/${id}/checkin/`,  { at }).then(r => r.data);
export const checkOut = (id, at) =>
  api.post(`shift-attendances/${id}/checkout/`, { at }).then(r => r.data);


// ドライバー勤怠

export const getDriver = (id) =>
  api.get(`drivers/${id}/`).then(r => r.data)

export const getDriverShift = shiftId =>
  api.get(`driver-shifts/${shiftId}/`).then(r => r.data)

/* ★ 一覧（STAFF 権限で全員分） */
export const getAllDriverShifts = (params = {}) =>
  api.get('driver-shifts/', { params }).then(r => r.data)

export function clockIn(driverId, { float_start = 0, at = null }) {
  // 共通の api インスタンスを使う！（token も baseURL も自動付与）
  return api.post(
    `driver-shifts/${driverId}/clock_in/`,
    { float_start, at }
  ).then(r => r.data)
}

export const clockOut = (shiftId, payload) =>
  api.patch(`driver-shifts/${shiftId}/clock_out/`, payload).then(r => r.data)



// 経費
export const createExpenseEntry  = payload      => api.post('expenses/',      payload).then(r => r.data);
export const updateExpenseEntry  = (id, payload) => api.patch(`expenses/${id}/`, payload).then(r => r.data);

export const deleteExpenseEntry  = id           => api.delete(`expenses/${id}/`);

export const getExpenseEntries = params =>
  api.get('expenses/', { params }).then(r => r.data);

export const getExpenseCategories = (params = {}) =>
  api.get('expense-categories/', { params }).then(r => r.data);


/* ---------- P/L API（デイリー／マンスリー／イヤーリー） ---------- */

/**
 * マンスリー P/L
 *   month : 'YYYY-MM'
 */
export const getMonthlyPL = (month, store = '') =>
  api.get('pl/monthly/', { params: { month, store } }).then(r => r.data)

/**
 * イヤーリー P/L（12ヶ月サマリ）
 *   year : 2025 など数値
 */
export const getYearlyPL = (year, store = '') =>
  api.get('pl/yearly/', { params: { year, store } }).then(r => r.data)



// 予約―ドライバー取得
export const getReservationDrivers = params =>
  api.get('reservation-drivers/', { params }).then(r => r.data)

// 追加・更新・削除
export const createReservationDriver = p => api.post('reservation-drivers/', p)
export const updateReservationDriver = (id, p) => api.patch(`reservation-drivers/${id}/`, p)
export const deleteReservationDriver = id => api.delete(`reservation-drivers/${id}/`)




/* ------------------------------------------------------------------ */
/* Bills キャバクラ版への移植版。現在のメイン
/* ------------------------------------------------------------------ */


// すでに baseURL が `/api/` なので “billing/...” を付ける

export const fetchBills   = (params={}) =>
  api.get('billing/bills/', { params }).then(r=>r.data)

export const fetchBill    = id      => api.get(`billing/bills/${id}/`).then(r=>r.data)

export const createBill = (tableId = 1) =>
  api.post('billing/bills/', { table: tableId }).then(r => r.data)

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
export const fetchCastShifts = (params = {}) =>
    api.get('billing/cast-shifts/', { params }).then(r => r.data)

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
  api.get('billing/cast-rankings/', { params }).then(r => r.data)


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
export const getStoreNotice = id =>
  api.get(`billing/store-notices/${id}/`).then(r => r.data);


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

export const updateStoreNotice = (id, payload) =>
  api.patch(`billing/store-notices/${id}/`, payload).then(r => r.data)

// 削除
export const deleteStoreNotice = id =>
  api.delete(`billing/store-notices/${id}/`);
