// src/api.js
import axios from 'axios'
import { setupCache } from 'axios-cache-interceptor'
import 'nprogress/nprogress.css'
import { wireInterceptors } from '@/api/interceptors'
import dayjs from 'dayjs'

// ★ baseURL は必ず相対 /api/（Viteのproxyを使う）
const RAW = import.meta.env.VITE_API_BASE ?? '/api';
const baseURL = (RAW + '/').replace(/\/+$/, '/'); // ← 末尾 / を強制で1本に

// ★ axios にキャッシュ機能を付与（10分・サーバのETag等も尊重）
export const api = setupCache(
	axios.create({ baseURL }),
	{ ttl: 10 * 60 * 1000, interpretHeader: true }
)

/* ------------------------------------------------------------------ */
/* interceptor: “ログイン系 URL には token を付けない”                    */
/* ------------------------------------------------------------------ */

// インターセプタを装着（/api/me はStore非依存 = デフォのskipStore['me/']のみ）
// 既存の認証/Store付与など（これは先に装着でOK）
wireInterceptors(api)

// ★ ここから “キャッシュ制御 & デバッグ” を追加
api.interceptors.request.use(cfg => {
	// 開発ログ
	// if (import.meta.env.DEV) console.log('[REQ]', cfg.baseURL, cfg.url, cfg.headers?.['X-Store-Id'])

	// 非GETはキャッシュしない
	const method = (cfg.method || 'get').toLowerCase()
	if (method !== 'get') { cfg.cache = false; return cfg }

	// パス判定（絶対URLでも動くように先頭の https://... を剥がす）
  const path = String(cfg.url || '')
    .replace(/^https?:\/\/[^/]+/i, '')
    .replace(/^\/+/, '')

  const noCache =
    path.startsWith('dj-rest-auth') ||
    path.startsWith('auth/') ||
    path.startsWith('me') ||
    path.startsWith('billing/kds/') ||
    /^billing\/bills(\/|$)/.test(path) ||       // ← 伝票リスト/個票は常に最新
    path.startsWith('billing/cast-shifts/')     // ← シフトも常に最新
  if (noCache) { cfg.cache = false; return cfg }

	// ⚠️ Store違いでキャッシュが混ざらないよう、疑似パラメータで分離
	const sid = localStorage.getItem('store_id')
	if (sid) cfg.params = { ...(cfg.params || {}), _sid: sid }

	return cfg
})

// api.interceptors.response.use(
// 	res => {
// 		// axios-cache-interceptor は res.cached を持つ
// 		if (import.meta.env.DEV) console.log('[RES]', res.config.url, res.status, res.cached ? 'HIT' : 'MISS')
// 		return res
// 	},
// 	err => {
// 		if (import.meta.env.DEV) console.warn('[ERR]', err.config?.url, err.response?.status, err.message)
// 		return Promise.reject(err)
// 	}
// )

// デバッグ用に叩けるよう公開
if (import.meta.env.DEV) window.__API__ = api



/* ------------------------------------------------------------------ */
/* 認証 API                                                            */
/* ------------------------------------------------------------------ */

/* 認証系はauth.jsで統一 */


/* ------------------------------------------------------------------ */
/* Bills キャバクラ版への移植版。現在のメイン
/* ------------------------------------------------------------------ */


// すでに baseURL が `/api/` なので “billing/...” を付ける


export const fetchBill = (id, { noCache=false } = {}) =>
  api.get(`billing/bills/${id}/`, noCache ? { cache:false } : undefined)
     .then(r => r.data)

// 一覧リロード用の helper（任意。なければ store 側で api.get を直叩きでOK）
export const fetchBillsList = ({ params={}, noCache=false } = {}) =>
  api.get('billing/bills/', {
    params,
    ...(noCache ? { cache:false } : {})
  }).then(r => Array.isArray(r.data?.results) ? r.data.results : (Array.isArray(r.data) ? r.data : []))

  export const fetchBills = (params = {}) =>
  fetchBillsList({ params, noCache: true })


export const createBill = (arg = {}) => {
	const payload = (typeof arg === 'number') ? { table_id: arg } : { ...arg }
	const body = {
		table_id    : payload.table_id ?? payload.table ?? null,
		opened_at   : payload.opened_at,               // 任意
		expected_out: payload.expected_out ?? null,    // 任意
		...(payload.memo != null ? { memo: String(payload.memo) } : {}),
	}
	return api.post('billing/bills/', body).then(r => r.data)
}


 export const deleteBill = id =>
   api.delete(`billing/bills/${id}/`)
 
export const addBillItem  = (id,p)  => 
  api.post(`billing/bills/${id}/items/`, p).then(r => r.data)

 export const closeBill = (id, payload = {}) =>
   api.post(`billing/bills/${id}/close/`, payload).then(r => r.data)
 
export const fetchMasters = () => api.get('billing/item-masters/', { 
  params: { _t: Date.now() },
  headers: { 'Cache-Control': 'no-cache' }
}).then(r=>r.data)

export const fetchCasts   = () => api.get('billing/casts/').then(r => r.data.results ?? r.data)

// 追記：メモだけ更新
export const updateBillMemo = (id, memo) =>
  api.patch(`billing/bills/${id}/`, { memo: String(memo ?? '') }).then(r => r.data)


/**
 * 指名／場内／フリーの配列をまとめて PATCH
 *   nomIds  = 本指名キャスト ID[]
 *   inIds   = 場内キャスト ID[]
 *   freeIds = フリー在席キャスト ID[]
 */
export const updateBillCasts = (
  billId,
  { nomIds = [], inIds = [], freeIds = [], dohanIds = [] } = {}
) => {
  // freeIds から本指名・同伴を除外（送信ノイズ低減）
  const filteredFree = (freeIds || []).filter(id => !nomIds.includes(id) && !dohanIds.includes(id))
  const body = {
    nominated_casts_w : nomIds, // 本指名（WRITE専用フィールド）
    inhouse_casts_w : inIds,    // 場内
    free_ids        : filteredFree,  // フリー（本指名/同伴除外後）
  }
  if (dohanIds && dohanIds.length) body.dohan_ids = dohanIds  // ★同伴（ある時だけ送る）
  return api.patch(`billing/bills/${billId}/`, body).then(res => res.data)
}

// 追加：同伴を1人だけ ON にする（既存があればPATCH、無ければPOST）
export const setBillDohan = async (billId, castId) => {
  // 既存 stay を特定（PATCH用に一度だけ取得）
  const bill = await fetchBill(billId).catch(() => null)
  const stay = (bill?.stays || []).find(s => !s.left_at && Number(s?.cast?.id) === Number(castId))

  if (stay?.id) {
    await api.patch(`billing/bills/${billId}/stays/${stay.id}/`, { stay_type: 'dohan' })
  } else {
    await api.post(`billing/bills/${billId}/stays/`, { cast_id: castId, stay_type: 'dohan' })
  }
  // 呼び出し側で同じパターンにしたいので常に最新Billを返す
  const fresh = await fetchBill(billId)
  return fresh
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

export const getBillingCasts = (params = {}, opt = {}) =>
  api.get('billing/casts/', { params, ...opt }).then(r => r.data)


/* ---------- キャスト売上 ---------- */
export const fetchCastSalesSummary = (params = {}) =>
  api.get('billing/cast-sales/', { params }).then(r => r.data)


export const fetchCastSalesDetail = (castId, params = {}) =>
  api.get('billing/cast-payouts/', {
    params: { cast: castId, ...params }
  }).then(r => r.data)
  

// キーの正規化: from/to を date_from/date_to へ
const _normalizeRange = (p = {}) => {
  const out = { ...p }
  if (out.from && !out.date_from) out.date_from = out.from
  if (out.to   && !out.date_to)   out.date_to   = out.to
  delete out.from; delete out.to
  return out
}

export const fetchCastItemDetails = (castId, params = {}) =>
  api.get('billing/cast-item-details/', {
    params: { cast: castId, ..._normalizeRange(params) }
  }).then(r => r.data)


// CastPayout を期間指定で一覧取得（全キャスト分）。limit大きめでページング回避
export const listCastPayouts = async (params = {}) => {
  const q = { limit: 10000, ...params }   // 必要ならもっと上げる
  const { data } = await api.get('billing/cast-payouts/', { params: q, cache: false })
  return Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
}
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
export const fetchStaffs = (params = {}, opt = {}) => {
  const kw = String(params?.q || params?.search || params?.name || '').trim()
  const cfg = { params, ...(opt || {}) }
  if (kw) cfg.cache = false            // ← 検索はキャッシュ無効
  // 追加の保険：クエリにタイムスタンプを付与（中間プロキシ対策）
  if (kw) cfg.params = { ...cfg.params, _ts: Date.now() }
  return api.get('billing/staffs/', cfg).then(r => r.data.results ?? r.data)
}

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


/** 手入力割引行（manual_discounts）だけを全入れ替えで保存 */
export const updateBillManualDiscounts = (billId, rows = []) => {
  const normalized = (rows || [])
    .map((r, i) => ({
      label: String(r.label || '').trim(),
      amount: Number(r.amount || 0),
      sort_order: r.sort_order ?? i,
    }))
    .filter(r => r.label && r.amount > 0)
  return patchBill(billId, { manual_discounts: normalized })
}


/**
 * 会計関連のパッチをまとめて送るユーティリティ
 * 例）settleBill(123, { memo, discount_rule, manual_discounts, settled_total, paid_cash, paid_card })
 */
export const settleBill = (billId, payload = {}) => {
  const body = {}
  if (payload.memo != null)            body.memo = String(payload.memo)
  if (payload.discount_rule !== undefined)
                                       body.discount_rule = (payload.discount_rule == null ? null : Number(payload.discount_rule))
  if (payload.manual_discounts !== undefined) {
    body.manual_discounts = (payload.manual_discounts || [])
      .map((r, i) => ({
        label: String(r.label || '').trim(),
        amount: Number(r.amount || 0),
        sort_order: r.sort_order ?? i,
      }))
      .filter(r => r.label && r.amount > 0)
  }
  if (payload.settled_total != null)   body.settled_total = Number(payload.settled_total)
  if (payload.paid_cash  != null)      body.paid_cash     = Number(payload.paid_cash)
  if (payload.paid_card  != null)      body.paid_card     = Number(payload.paid_card)
  return patchBill(billId, body)
}


/**
 * ① settleBill（PATCH）→ ② closeBill（POST） の順で会計確定
 *   payload は settleBill と同じ形（memo/discount_rule/manual_discounts/settled_total/paid_*）
 */
export const patchAndCloseBill = async (billId, payload = {}) => {
  await settleBill(billId, payload)
  const st = payload?.settled_total != null ? Number(payload.settled_total) : undefined
  return closeBill(billId, st != null ? { settled_total: st } : {})
}


// --- granular wrapper ----------------------
export const updateBillTimes = (id, { opened_at, expected_out }) =>
  patchBill(id, { opened_at, expected_out })

export const updateBillCustomers = (id, customer_ids = []) => {
  const ids = (customer_ids || []).map(v => (typeof v === 'object' ? v.id : v)).filter(Boolean)
  return patchBill(id, { customer_ids: ids })
}

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

// 検索（名前・電話）
export const searchCustomers = (q = '') =>
  api.get('billing/customers/', {
    params: q
      ? { q }
      : { ordering: '-id', limit: 50 }   // ← 何も入力されてなければ最新50件
  }).then(r => r.data?.results ?? r.data ?? []);

// 新規作成（最低限のフィールドだけマップ）
export const createCustomer = (payload = {}) => {
  const body = {
    full_name: payload.name  ?? '',
    phone    : payload.phone ?? '',
    memo     : payload.memo  ?? '',
    // バックエンドの Customer には addresses 無いので無視
  };
  return api.post('billing/customers/', body).then(r => r.data);
};

export const updateCustomer = (id, payload = {}) => {
  const body = {
    full_name: payload.full_name ?? payload.name ?? '',
    phone    : payload.phone     ?? '',
    memo     : payload.memo      ?? '',
    alias    : payload.alias     ?? '',
    birthday : payload.birthday  ?? null,
  };
  return api.patch(`billing/customers/${id}/`, body).then(r => r.data);
};

export const deleteCustomer = id =>
  api.delete(`billing/customers/${id}/`);

// bill に items が含まれない場合のフォールバック用
export const fetchBillItemsByBillId = (billId) =>
  api.get('/billing/bill-items/', { params:{ bill: billId, ordering:'id' } })
     .then(r => Array.isArray(r.data?.results) ? r.data.results : (Array.isArray(r.data) ? r.data : []))


/* ---------- 席指定と席ごとのサービス料 ---------- */
export const fetchStoreSeatSettings = () =>
  api.get('billing/store-seat-settings/').then(r => r.data)

// 現在店舗に適用されている席種だけを {id,label} 配列で返す
export const fetchSeatTypesForCurrentStore = async () => {
  const list = await fetchStoreSeatSettings()
  const uniq = new Map()
  for (const s of (Array.isArray(list) ? list : [])) {
    if (s && s.seat_type != null) {
      uniq.set(s.seat_type, s.seat_type_display || `#${s.seat_type}`)
    }
  }
  return Array.from(uniq, ([id, label]) => ({ id: Number(id), label: String(label) }))
}


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
  const res = await api.get('billing/order-events/', {
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


// --- Cast Goals (キャスト本人の目標) -----------------------------

/**
 * 一覧取得
 * GET /billing/casts/{castId}/goals/
 */
export const listCastGoals = (castId, { active = true } = {}) =>
  api.get(`billing/casts/${castId}/goals/`, {
    params: active == null ? {} : { active: active ? 1 : 0 },
    // ゴールは最新状態が大事なのでキャッシュ無効
    cache: false,
  }).then(r => r.data);

/**
 * 作成
 * POST /billing/casts/{castId}/goals/
 * payload 例:
 * {
 *   metric: 'sales_amount' | 'nominations_count' | 'inhouse_count' | 'champagne_revenue' | 'champagne_bottles',
 *   target_value: number,
 *   period_from: 'YYYY-MM-DD',
 *   period_to:   'YYYY-MM-DD'
 * }
 */
export const createCastGoal = (castId, payload) =>
  api.post(`billing/casts/${castId}/goals/`, payload, { cache: false }).then(r => r.data);

/**
 * 削除(アーカイブでもOK。サーバ側が is_archived を立てる実装なら PATCH に差し替え)
 * DELETE /billing/casts/{castId}/goals/{goalId}/
 */
export const deleteCastGoal = (castId, goalId) =>
  api.delete(`billing/casts/${castId}/goals/${goalId}/`, { cache: false });



// === 追加: 割引ルール API ===============================

// 一覧（そのまま使える汎用）
// 返り値は配列に正規化（results/配列どちらでも対応）
export const fetchDiscountRules = (params = {}) =>
  api.get('billing/discount-rules/', { params })
     .then(r => Array.isArray(r.data?.results) ? r.data.results
              : Array.isArray(r.data)          ? r.data
              : [])

// Basicsパネル用（is_active & is_basic）
export const fetchBasicDiscountRules = () =>
  fetchDiscountRules({ is_active: true, is_basic: true })

// Billに割引ルールをセット（idを直接指定）
export const updateBillDiscountRule = (billId, ruleId /* number|null|undefined */) => {
  // 初期マウント時の未確定値は無視（送らない）
  if (ruleId === undefined) return Promise.resolve();
  return patchBill(billId, { discount_rule: ruleId === null ? null : Number(ruleId) });
};

export const setBillDiscountByCode = async (billId, code) => {
  if (code === undefined) return Promise.resolve(); // 初期未確定は無視
  if (!code) return updateBillDiscountRule(billId, null);
  const list = await fetchDiscountRules({ is_active: true, code }); // code はサーバではフィルタされないがOK
  const rule = (Array.isArray(list) ? list : []).find(r => String(r.code) === String(code));
  return updateBillDiscountRule(billId, rule?.id ?? null);
};



// ───────── 給与計算 ─────────

// 一覧（キャストごとの集計）
export async function fetchPayrollSummary(params = {}) {
  const res = await api.get('billing/payroll/summary/', { params })
  return res.data
}

// 詳細（シフト行＋歩合行）
export async function fetchPayrollDetail(castId, params = {}) {
  const res = await api.get(`billing/payroll/casts/${castId}/`, { params })
  return res.data
}

export async function downloadPayrollDetailCsv(castId, params = {}) {
  // axiosインスタンス(api)は認証＆X-Store-Idを自動付与
  const res = await api.get(`billing/payroll/casts/${castId}/export.csv`, {
    params,
    responseType: 'blob',
  })
  return res.data // Blob
}


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


if (import.meta.env.DEV) window.__API__ = api



