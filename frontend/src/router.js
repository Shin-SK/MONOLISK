// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import { useUser } from '@/stores/useUser'

/* --- レイアウト --- */
import AdminLayout      from '@/layouts/AdminLayout.vue'
import CastLayout       from '@/layouts/CastLayout.vue'

const routes = [
  // ---------- キャバクラ版 ---------- //
  {
  path: '/bills',
    component: AdminLayout,
    meta: { requiresAuth: true, adminOnly: true },
    children: [
          { path: '/', redirect: '/dashboard' },
          { path: '/dashboard',   component: () => import('@/views/DashboardAdmin.vue'), meta: { title: 'DASHBOARD' }},
          { path: '/dashboard/list',   component: () => import('@/views/DashboardList.vue'), meta: { title: 'DASHBOARD-LIST' }},
          { path: '/dashboard/timeline',   component: () => import('@/views/DashboardGantt.vue'), meta: { title: 'DASHBOARD-TIMELINE' }},
          { path: '', component: () => import('@/views/DashboardList.vue'), meta: { title: '伝票' }},
          { path: 'pl/daily', component: () => import('@/views/BillPLDaily.vue'), meta: { title: '売上-日次' }},
          { path: 'pl/Monthly', component: () => import('@/views/BillPLMonthly.vue'), meta: { title: '売上-月次' }},
          { path: 'pl/yearly',  component: () => import('@/views/BillPLYearly.vue'), meta: { title: '売上-年次' } },
          { path: '/cast-sales', component: () => import('@/views/CastSalesList.vue'), meta: { title: 'キャスト売上' } },
          { path: '/casts', component: () => import('@/views/AdminCastList.vue'), meta: { title: 'キャスト情報' } },
          { path: '/cast-sales/:id', component: () => import('@/views/CastSalesDetail.vue'), props: true, name: 'cast-sales-detail', meta: { title: 'キャスト売上' } },
          { path: 'cast-shift', component: () => import('@/views/CastShiftList.vue'), props: true, meta: { title: 'シフト管理' } },
          { path: 'cast-shift/:id/shifts', component: () => import('@/views/CastShiftPage.vue'), props: true ,name: 'cast-shift-page', meta: { title: 'シフト管理' } },
          { path: '/ranking', component: () => import('@/views/CastRanking.vue'), props: true, meta: { title: 'ランキング' } },
          { path: '/staff', component: () => import('@/views/AdminStaffList.vue'), props: true, meta: { title: 'スタッフ情報' } },
          { path: '/staff/:id', component: () => import('@/views/AdminStaffForm.vue'), props: true, meta: { title: 'スタッフ情報-詳細' } },
          { path: '/table', component: () => import('@/components/BillListTable.vue'), props: true, meta: { title: 'テーブルビュー' }},
    ],
  },

  // ---------- キャスト ---------- //
  {
    path: '/cast',
    component: CastLayout,
    meta: { requiresAuth: true }, // ★ 後で castOnly へ
    children: [
      { path: '', redirect: '/cast/mypage' },
      { path: 'mypage/:id(\\d+)', component: () => import('@/views/CastMypage.vue'), name: 'cast-mypage',meta: { title: 'MyPage' } },
      { path: 'sales', component: () => import('@/views/CastSalesDetail.vue') },
    ],
  },

  // ---------- その他認証系 ---------- //
 { path: '/login', component: () => import('@/views/Login.vue') },

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



