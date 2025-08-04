// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import { useUser } from '@/stores/useUser'

/* --- レイアウト --- */
import AdminLayout      from '@/layouts/AdminLayout.vue'
import ReservationLayout from '@/layouts/ReservationLayout.vue' // スタッフ共通
import DriverLayout     from '@/layouts/DriverLayout.vue'
import CastLayout       from '@/layouts/CastLayout.vue'

/* --- 画面 --- */
import ReservationList       from '@/views/ReservationList.vue'
import ReservationFormAdmin  from '@/views/ReservationFormAdmin.vue'
import ReservationFormDriver from '@/views/ReservationFormDriver.vue'
import Login                 from '@/views/Login.vue'
import TimelineAdmin         from '@/views/TimelineAdmin.vue'
import DriverMypage        from '@/views/DriverMypage.vue'
import CustomerList          from '@/views/CustomerList.vue'
import CustomerForm          from '@/views/CustomerForm.vue'
import AdminCastList              from '@/views/AdminCastList.vue'
import AdminCastForm              from '@/views/AdminCastForm.vue'
import AdminDriverList              from '@/views/AdminDriverList.vue'
import AdminDriverForm              from '@/views/AdminDriverForm.vue'
import UserProfileEdit              from '@/views/UserProfileEdit.vue'
import Sales           from '@/views/Sales.vue'
import PLMonthly           from '@/views/PLMonthly.vue'
import PLDaily  from '@/views/PLDaily.vue'
import PLYearly  from '@/views/PLYearly.vue'
import ExpenseForm  from '@/views/ExpenseForm.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },

  /* ---------- 管理者 ---------- */
  {
    path: '/',
    component: AdminLayout,
    meta: { requiresAuth: true, adminOnly: true },
    children: [
      { path: 'dashboard',   component: () => import('@/views/DashboardAdmin.vue'), meta: { title: 'DASHBOARD' }},          // /admin
      { path: 'reservations', component: ReservationList, meta: { title: '予約一覧' } },
      { path: 'reservations/new',     component: ReservationFormAdmin, meta: { title: '新規予約' } },
      { path: 'reservations/:id',     component: ReservationFormAdmin, name: 'admin-reservation-detail', meta: { title: '予約詳細' } },
      { path: 'reservations/:id(\\d+)', component: ReservationFormAdmin, meta: { title: '予約詳細' }},
      { path: 'timeline',             component: TimelineAdmin },
      { path: 'customers',            component: CustomerList, meta: { title: '顧客情報' }},
      { path: 'customers/new',        component: CustomerForm, meta: { title: '新規顧客' }},
      { path: 'customers/:id',        component: CustomerForm, meta: { title: '顧客編集' } },
      { path: 'casts',                component: AdminCastList, meta: { title: 'キャスト情報' } },
      { path: 'casts/new',            component: AdminCastForm, meta: { title: '新規キャスト' } },
      { path: 'casts/:id',            component: AdminCastForm, meta: { title: 'キャスト編集' } },
      { path: 'drivers',                component: AdminDriverList, meta: { title: 'ドライバー情報' } },
      { path: 'drivers/new',            component: AdminDriverForm, meta: { title: '新規ドライバー' } },
      { path: 'drivers/:id',            component: AdminDriverForm, meta: { title: 'ドライバー編集' } },
      { path: '/driver-shifts', name: 'driver-shift-list', component: () => import('@/views/DriverShiftList.vue')},
      {
        path: '/driver-shifts/driver/:driverId(\\d+)',   // ★NEW
        name: 'driver-shift-by-driver',
        component: () => import('@/views/DriverShift.vue'),
        props: true   // → route.params.driverId で受け取れる
      },
      {
        path: '/driver-shifts/:shiftId(\\d+)',   // id? → shiftId 固定
        name: 'driver-shift-detail',
        component: () => import('@/views/DriverShift.vue'),
        props: true
      },
      // { path: 'cast-shifts', component: () => import('@/views/CastShift.vue') },
      { path: 'sales', component: Sales },
      /* ---------- PL ---------- */
      { path: '/pl/monthly', component: PLMonthly },
      { path: '/pl/daily', component: PLDaily },
      { path: '/pl/yearly', component: PLYearly },
      { path: '/expense/form', component: ExpenseForm },
    ],
  },

  /* ---------- スタッフ（予約管理だけ欲しい場合） ---------- */
  {
    path: '/staff',
    component: ReservationLayout,      // サイドバーなどスタッフ用外枠
    meta: { requiresAuth: true },
    children: [
      { path: 'reservations',          component: ReservationList },    // /reservation
      { path: 'reservations/:id',       component: ReservationFormAdmin, name: 'staff-reservation-detail' },
      { path: 'reservations/new',       component: ReservationFormAdmin },
    ],
  },

  /* ---------- ドライバー ---------- */
  {
    path: '/driver',
    component: DriverLayout,
    meta: { requiresAuth: true, driverOnly: true },
    children: [
      { path: '', redirect: '/driver/mypage' },
      { path: 'mypage',        component: DriverMypage },
      { path: 'reservations/:id', component: ReservationFormDriver },
      { path: 'profile', component: UserProfileEdit }   // /driver/profile など

    ],
  },

  /* ---------- 認証 ---------- */
  { path: '/login', component: Login },


  /* ---------- キャバクラ編 伝票 ---------- */
  {
  path: '/bills',
    component: AdminLayout,
    meta: { requiresAuth: true, adminOnly: true },
    children: [
          { path: '', component: () => import('@/views/BillList.vue'), meta: { title: '伝票' }},
          { path: 'pl/daily', component: () => import('@/views/BillPLDaily.vue'), meta: { title: '売上-日次' }},
          { path: 'pl/Monthly', component: () => import('@/views/BillPLMonthly.vue'), meta: { title: '売上-月次' }},
          { path: 'pl/yearly',  component: () => import('@/views/BillPLYearly.vue'), meta: { title: '売上-年次' } },
          { path: '/cast-sales', component: () => import('@/views/CastSalesList.vue'), meta: { title: 'キャスト売上' } },
          { path: '/cast-sales/:id', component: () => import('@/views/CastSalesDetail.vue'), props: true, name: 'cast-sales-detail', meta: { title: 'キャスト売上' } },
          { path: 'cast-shift', component: () => import('@/views/CastShiftList.vue'), props: true, meta: { title: 'シフト管理' } },
          { path: 'cast-shift/:id/shifts', component: () => import('@/views/CastShiftPage.vue'), props: true ,name: 'cast-shift-page', meta: { title: 'シフト管理' } },
          { path: '/ranking', component: () => import('@/views/CastRanking.vue'), props: true, meta: { title: 'ランキング' } },
    ]
  },

  {
    path: '/cast',
    component: CastLayout,
    meta: { requiresAuth: true }, // ★ 後で castOnly へ
    children: [
      { path: '', redirect: '/cast/mypage' },

      // マイページは「必ず :id を付ける」形に
      { path: 'mypage/:id(\\d+)', component: () => import('@/views/CastMypage.vue'), name: 'cast-mypage',meta: { title: 'MyPage' } },

      { path: 'sales', component: () => import('@/views/CastSalesDetail.vue') },
      { path: 'profile', component: UserProfileEdit },
    ],
  },



]

const router = createRouter({
  history: createWebHistory(),
  routes,
})







/* ---- ルートガード（ほぼ元のまま／親メタを見るだけ） ---- */
router.beforeEach(async (to, _from, next) => {
  const userStore = useUser()
  await userStore.fetch()

  const loggedIn = Object.keys(userStore.info || {}).length > 0
  if (!loggedIn && to.path !== '/login') return next('/login')

  /* 親も含めたメタ判定 */
  const meta = (key) => to.matched.some(r => r.meta[key])

  const defaultPath =
    userStore.isCast   ? '/cast/mypage'  :
    userStore.isDriver ? '/driver/mypage'         :
    userStore.isStaff  ? '/reservations' 
                            : '/staff/reservations';

    if (to.path === '/' || (to.path === '/login' && loggedIn))
    return next(defaultPath)

  if (meta('adminOnly')  && !userStore.isStaff)  return next(defaultPath)
  if (meta('castOnly')   && !userStore.isCast)   return next(defaultPath)
  if (meta('driverOnly') && !userStore.isDriver) return next(defaultPath)

  next()
})

export default router



