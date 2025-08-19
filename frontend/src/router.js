// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getStoreId } from '@/auth'

/* --- レイアウト --- */
import MainLayout from '@/layouts/MainLayout.vue'
import CastLayout from '@/layouts/CastLayout.vue'

// （必要なら）import { useLoading } from '@/stores/useLoading'

const routes = [
  // ---------- キャバクラ版 ---------- //
  {
    path: '/bills',
    component: MainLayout,
    meta: { requiresAuth: true, adminOnly: true },
    children: [
      // ★ rootは別でガードするため、ここは残してOK（/→/dashboard）
      { path: '/', redirect: '/dashboard' },

      // ★ 絶対パスの子ルートにも requiresAuth を明示付与
      { path: '/dashboard',            component: () => import('@/views/DashboardAdmin.vue'), meta: { title: 'DASHBOARD',            requiresAuth: true, adminOnly: true }},
      { path: '/dashboard/list',       component: () => import('@/views/DashboardList.vue'),  meta: { title: 'DASHBOARD-LIST',       requiresAuth: true, adminOnly: true }},
      { path: '/dashboard/timeline',   component: () => import('@/views/DashboardGantt.vue'), meta: { title: 'DASHBOARD-TIMELINE',   requiresAuth: true, adminOnly: true }},

      { path: '', component: () => import('@/views/DashboardList.vue'), meta: { title: '伝票' }},

      { path: 'pl/daily',    component: () => import('@/views/BillPLDaily.vue'),   meta: { title: '売上-日次' } },
      { path: 'pl/Monthly',  component: () => import('@/views/BillPLMonthly.vue'), meta: { title: '売上-月次' } },
      { path: 'pl/yearly',   component: () => import('@/views/BillPLYearly.vue'),  meta: { title: '売上-年次' } },

      { path: '/cast-sales',           component: () => import('@/views/CastSalesList.vue'),   meta: { title: 'キャスト売上', requiresAuth: true, adminOnly: true } },
      { path: '/cast-sales/:id',       component: () => import('@/views/CastSalesDetail.vue'), props: true, name: 'cast-sales-detail', meta: { title: 'キャスト売上', requiresAuth: true, adminOnly: true } },
      { path: 'cast-shift',            component: () => import('@/views/CastShiftList.vue'),   props: true, meta: { title: 'シフト管理' } },
      { path: 'cast-shift/:id(\\d+)/shifts', component: () => import('@/views/CastShiftPage.vue'), props: true ,name: 'cast-shift-page', meta: { title: 'シフト管理' } },

      { path: '/ranking',   component: () => import('@/views/CastRanking.vue'),        props: true, meta: { title: 'ランキング',    requiresAuth: true, adminOnly: true } },
      { path: '/table',     component: () => import('@/components/BillListTable.vue'), props: true, meta: { title: 'テーブルビュー', requiresAuth: true, adminOnly: true }},
      { path: '/customers', component: () => import('@/views/CustomerPage.vue'),       props: true, meta: { title: '顧客情報',      requiresAuth: true, adminOnly: true }},

      { path: '/staff/:id(\\d+)', redirect: to => ({ name: 'settings-staff-form', params: { id: to.params.id } }) },
      { path: '/staffs/new',      redirect: { name: 'settings-staff-new' } },
      { path: '/casts/:id(\\d+)', redirect: to => ({ name: 'settings-cast-form', params: { id: to.params.id } }) },
      { path: '/casts/new',       redirect: { name: 'settings-cast-new' } },
    ],
  },

  {
    path: '/settings',
    component: MainLayout,
    meta: { requiresAuth: true, adminOnly: true, title: '設定' },
    children: [
      {
        path: '',
        name: 'settings',
        component: () => import('@/views/settings/GlobalSetting.vue'),
        children: [
          { path: 'store',           name: 'settings-store',      component: () => import('@/views/settings/StoreSetting.vue') },
          { path: 'menu',            name: 'settings-menu',       component: () => import('@/views/settings/MenuSetting.vue') },
          { path: 'table',           name: 'settings-table',      component: () => import('@/views/settings/TableSetting.vue') },
          { path: 'staff',           name: 'settings-staff-list', component: () => import('@/views/settings/AdminStaffList.vue') },
          { path: 'staff/:id(\\d+)', name: 'settings-staff-form', component: () => import('@/views/settings/AdminStaffForm.vue'), props: true },
          { path: 'staff/new',       name: 'settings-staff-new',  component: () => import('@/views/settings/AdminStaffForm.vue') },
          { path: 'casts',           name: 'settings-cast-list',  component: () => import('@/views/settings/AdminCastList.vue') },
          { path: 'casts/new',       name: 'settings-cast-new',   component: () => import('@/views/settings/AdminCastForm.vue') },
          { path: 'casts/:id(\\d+)', name: 'settings-cast-form',  component: () => import('@/views/settings/AdminCastForm.vue'), props: true },
          { path: 'news',            name: 'settings-news-list',  component: () => import('@/views/settings/AdminNewsList.vue') },
          { path: 'news/new',        name: 'settings-news-new',   component: () => import('@/views/settings/AdminNewsForm.vue') },
          { path: 'news/:id(\\d+)',  name: 'settings-news-form',  component: () => import('@/views/settings/AdminNewsForm.vue'), props: true },
        ],
      },
    ],
  },

  // ---------- キャスト ---------- //
  {
    path: '/cast',
    component: CastLayout,
    meta: { requiresAuth: true }, // ★ 後で castOnly へ
    children: [
      { path: '', redirect: '/cast/mypage' },
      { path: 'mypage/:id(\\d+)', component: () => import('@/views/CastMypage.vue'), name: 'cast-mypage', meta: { title: 'MyPage' } },
      {
        path: 'news/:id(\\d+)',
        name: 'news-detail',
        component: () => import('@/views/NewsDetail.vue'),
        props: route => ({ id: Number(route.params.id) }),
        meta: { title: 'お知らせ' },
      },
      { path: 'sales', component: () => import('@/views/CastSalesDetail.vue') },
    ],
  },

  // ---------- その他認証系 ---------- //
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },

  { path: '/casts',     redirect: { name: 'settings-cast-list' } },
  { path: '/staff',     redirect: { name: 'settings-staff-list' } },
  { path: '/casts/new', redirect: { name: 'settings-cast-new' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token   = getToken()
  const storeId = getStoreId()
  const requiresAuth = to.matched.some(r => r.meta?.requiresAuth)

  // ★ ルート直アクセス制御（未ログイン→/login、ログイン済→/dashboard）
  if (to.path === '/') {
    return next(token && storeId ? '/dashboard' : '/login')
  }

  // /login はフリーパス（ログイン済みならダッシュボードへ）
  if (to.name === 'login') {
    return next(token && storeId ? '/dashboard' : undefined)
  }

  // 認証必須なら token & store_id を要求
  if (requiresAuth && (!token || !storeId)) {
    return next({ path: '/login', query: { next: to.fullPath } })
  }

  next()
})

export default router
