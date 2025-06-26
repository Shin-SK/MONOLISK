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
import ReservationFormCast from '@/views/ReservationFormCast.vue'
import Login                 from '@/views/Login.vue'
import TimelineAdmin         from '@/views/TimelineAdmin.vue'
import CastMypage          from '@/views/CastMypage.vue'
import CastSales          from '@/views/CastSales.vue'
import DriverMypage        from '@/views/DriverMypage.vue'
import CustomerList          from '@/views/CustomerList.vue'
import CustomerForm          from '@/views/CustomerForm.vue'
import CastList              from '@/views/CastList.vue'
import CastForm              from '@/views/CastForm.vue'
import UserProfileEdit              from '@/views/UserProfileEdit.vue'
import ClosingList           from '@/views/ClosingList.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },

  /* ---------- 管理者 ---------- */
  {
    path: '/',
    component: AdminLayout,
    meta: { requiresAuth: true, adminOnly: true },
    children: [
      { path: 'dashboard',   component: () => import('@/views/DashboardAdmin.vue') },          // /admin
      { path: 'reservations', component: ReservationList },
      { path: 'reservations/new',     component: ReservationFormAdmin },
      { path: 'reservations/:id',     component: ReservationFormAdmin, name: 'admin-reservation-detail' },
      { path: 'timeline',             component: TimelineAdmin },
      { path: 'customers',            component: CustomerList },
      { path: 'customers/new',        component: CustomerForm },
      { path: 'customers/:id',        component: CustomerForm },
      { path: 'casts',                component: CastList },
      { path: 'casts/new',            component: CastForm },
      { path: 'casts/:id',            component: CastForm },
      { path: 'shifts', component: () => import('@/views/ShiftPlanAdmin.vue') },
      { path: 'closing',              component: ClosingList },
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

  /* ---------- キャスト ---------- */
  {
    path: '/cast',
    component: CastLayout,
    meta: { requiresAuth: true, castOnly: true },
    children: [
      { path: '', redirect: '/cast/mypage' },
      { path: 'mypage',        component: CastMypage },
      { path: 'reservations/:id', component: ReservationFormCast },
      { path:'sales', component: CastSales },
      { path: 'profile', component: UserProfileEdit }   // /cast/profile など
    ],
  },

  /* ---------- 認証 ---------- */
  { path: '/login', component: Login },
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
