// src/api.js
import axios from 'axios'
import qs        from 'qs'
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/',
})


/* ---------------------------------------- */
/* 共通レスポンスインターセプタ & パーサ     */
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

/* ❶ 401 専用（壊れたトークン掃除のみ） */
api.interceptors.response.use(
	res => res,
	err => {
		if (err.response?.status === 401) localStorage.removeItem('token')
		return Promise.reject(err)	// → 次(❷)へ
	}
)

/* ❷ 全エラー共通（alert で内容表示） */
api.interceptors.response.use(
	res => res,
	err => {
		alert(parseApiError(err))
		return Promise.reject(err)	// → 呼び出し元の catch へ
	}
)




/* ------------------------------------------------------------------ */
/* 1. interceptor: “ログイン系 URL には token を付けない”            */
/* ------------------------------------------------------------------ */
const SKIP_AUTH = [
  'dj-rest-auth/login/',
  'dj-rest-auth/registration/',
  'dj-rest-auth/password/reset/',
]

api.interceptors.request.use(cfg => {
  // 対象 URL ならスキップ
  if (!SKIP_AUTH.some(p => cfg.url.includes(p))) {
    const t = localStorage.getItem('token')
    if (t) cfg.headers.Authorization = `Token ${t}`
  }
  return cfg
})


api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')      // ← 壊れた token を掃除
    }
    return Promise.reject(err)
  }
)

/* ------------------------------------------------------------------ */
/* 2. 認証 API                                                         */
/* ------------------------------------------------------------------ */
export async function login(username, password) {
  localStorage.removeItem('token')                // ← まず完全クリア
  const { data } = await api.post(
    'dj-rest-auth/login/',
    { username, password },
    { headers: { Authorization: '' } }           // ← 念のため空ヘッダで上書き
  )
  localStorage.setItem('token', data.key)
}

export async function logout() {
  try { await api.post('dj-rest-auth/logout/') } catch (_) {}
  localStorage.removeItem('token')
}


/* ---------- Reservations ---------- */
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
export const getStores    = () => api.get('stores/?simple=1').then(simple)
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
 * デイリー P/L
 *   date  : 'YYYY-MM-DD'
 *   store : 店舗ID もしくは '' (全店)
 */
export const getDailyPL = (date, store = '') =>
  api.get('pl/daily/', { params: { date, store } }).then(r => r.data)

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




/* ---------- Bills ---------- */
// すでに baseURL が `/api/` なので “billing/...” を付ける

export const fetchBills   = ()      => api.get('billing/bills/').then(r=>r.data)
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

export const updateBillCasts = (
  billId,
  { nomIds = [], inIds = [], freeIds = [] }   // ★ 追加
) =>
  api.patch(`billing/bills/${billId}/`, {
    nominated_casts : nomIds,
    inhouse_casts_w : inIds,
    free_ids        : freeIds,	// ★ snake_case に合わせる
  }).then(r => r.data)

export const fetchTables = storeId =>
  api.get('billing/tables/', { params:{ store:storeId } }).then(r=>r.data)

export const deleteBillItem = (billId, itemId) =>
  api.delete(`billing/bills/${billId}/items/${itemId}/`)

export const getStore  = id => api.get(`billing/stores/${id}/`).then(r => r.data)



export const getBillDailyPL = (date, storeId = '') =>
  api.get('billing/pl/daily/', { params: { date, store_id: storeId } }).then(r => r.data)


export const getBillMonthlyPL = (monthStr, storeId = '') => {
  const [year, month] = monthStr.split('-').map(Number)
  return api.get('billing/pl/monthly/', {
    params: { year, month, store_id: storeId }
  }).then(r => r.data)
}

export const getBillYearlyPL = (year, storeId = '') =>
  api.get('billing/pl/yearly/', {
    params: { year, store_id: storeId }
  }).then(r => r.data)


// await api.post(`billing/bills/${bill.id}/items/`, {
//   item_master: draftMasterId.value,
//   qty: draftQty.value,
//   served_by_cast: draftCastId.value || null
// })
// Object.assign(bill, response.data)