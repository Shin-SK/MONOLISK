// src/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/',
  withCredentials: true,
});

// ★ ここで毎リクエスト直前に Cookie から csrftoken を拾って付与
api.interceptors.request.use(config => {
  const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  if (m) {
    config.headers['X-CSRFToken'] = decodeURIComponent(m[1]);
  }
  return config;
});

export default api;


axios.defaults.withCredentials = true;
axios.defaults.xsrfCookieName  = 'csrftoken';
axios.defaults.xsrfHeaderName  = 'X-CSRFToken';


/* ---------- Reservations ---------- */
export const getReservations = (params = {}) =>
  api.get('reservations/', { params }).then(r => r.data)

export const getReservation    = id      => api.get(`reservations/${id}/`).then(r => r.data)
export const createReservation = payload => api.post('reservations/', payload)
export const updateReservation = (id, p) => api.patch(`reservations/${id}/`, p)

/* ---------- マスター ---------- */
const simple = r => r.data
export const getStores    = () => api.get('stores/?simple=1').then(simple)
export const getCustomers = () => api.get('customers/?simple=1').then(simple)
export const getDrivers   = () => api.get('drivers/?simple=1').then(simple)
export const getCourses   = () => api.get('courses/?simple=1').then(simple)
export const getOptions   = () => api.get('options/').then(r => r.data)

/* ---------- キャスト & 料金 ---------- */
export const getCastProfiles = store =>
  api.get('cast-profiles/', { params: { store } })
     .then(r => r.data.results ?? r.data)

export const getPrice = (castProfile, course) =>
  api.get('pricing/', { params: { cast_profile: castProfile, course } })
     .then(r => r.data.price)

/* ---------- 顧客 ---------- */
export const searchCustomers = q =>
  api.get('customers/', { params: { phone: q } }).then(r => r.data)

export const createCustomer = p           => api.post('customers/', p).then(r => r.data)
export const updateCustomer = (id, p)     => api.put(`customers/${id}/`, p).then(r => r.data)
export const deleteCustomer = id          => api.delete(`customers/${id}/`)
export const getCustomer    = id          => api.get(`customers/${id}/`).then(r => r.data)

/* ---------- キャストオプション ---------- */
export const getCastOptions  = castId => api.get('cast-options/', { params: { cast_profile: castId } }).then(r => r.data)
export const patchCastOption = (id, p) => api.patch(`cast-options/${id}/`, p).then(r => r.data)
