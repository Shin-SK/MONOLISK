// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getStoreId } from '@/auth'
import { useUser } from '@/stores/useUser'

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
      // ★ 絶対パスの子ルートにも requiresAuth を明示付与
      { path: '/dashboard',            component: () => import('@/views/DashboardAdmin.vue'), meta: { title: 'DASHBOARD',            requiresAuth: true, adminOnly: true }},
      { path: '/dashboard/list',       component: () => import('@/views/DashboardList.vue'),  meta: { title: 'DASHBOARD-LIST',       requiresAuth: true, adminOnly: true }},
      { path: '/dashboard/timeline',   component: () => import('@/views/DashboardGantt.vue'), meta: { title: 'DASHBOARD-TIMELINE',   requiresAuth: true, adminOnly: true }},

      { path: '', component: () => import('@/views/DashboardList.vue'), meta: { title: '伝票' }},

      { path: 'pl/daily',    component: () => import('@/views/BillPLDaily.vue'),   meta: { title: '売上-日次', capsAny: ['view_pl_store','view_pl_multi'], requiresAuth:true } },
      { path: 'pl/Monthly',  component: () => import('@/views/BillPLMonthly.vue'), meta: { title: '売上-月次', capsAny: ['view_pl_store','view_pl_multi'], requiresAuth:true } },
      { path: 'pl/yearly',   component: () => import('@/views/BillPLYearly.vue'),  meta: { title: '売上-年次', capsAny: ['view_pl_store','view_pl_multi'], requiresAuth:true } },

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
      // 追加：KDSルート
      { path: '/kds/kitchen', component: () => import('@/views/KDSStation.vue'), meta: { title: 'KDS Kitchen', requiresAuth: true, kds: true } },
      { path: '/kds/drinker', component: () => import('@/views/KDSStation.vue'), meta: { title: 'KDS Drinker', requiresAuth: true, kds: true } },
      { path: '/kds/dishup',  component: () => import('@/views/KDSDishup.vue'),  meta: { title: 'KDS Deshap',  requiresAuth: true, kds: true } },

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
    children: [
      { path: '', redirect: '/cast/mypage' },
      { path: 'mypage', name: 'cast-mypage' , component: () => import('@/views/cast/Mypage.vue') },
      { path: 'order',  component: () => import('@/views/cast/Order.vue'), meta: { cap: 'cast_order_self' } },
      // ★ これを追加
      { path: 'news/:id(\\d+)', name: 'news-detail', component: () => import('@/views/NewsDetail.vue') },
    ],
  },
  // ---------- スタッフ ---------- //
  {
    path: '/staff',
    component: MainLayout,
    meta: { cap: 'operate_orders', title: 'STAFF' },
    children: [
      { path: 'mypage',  name: 'staff-mypage',  component: () => import('@/views/staff/StaffMypage.vue'),  meta:{ cap:'operate_orders', title:'MYPAGE' } },
    ]
  },


  // ---------- その他認証系 ---------- //
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },

  { path: '/casts',     redirect: { name: 'settings-cast-list' } },
  { path: '/staff',     redirect: { name: 'settings-staff-list' } },
  { path: '/casts/new', redirect: { name: 'settings-cast-new' } },
]

// --- ここから下を router.js の末尾に置き換え ---

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const KDS_ENABLED = import.meta.env.VITE_KDS_ENABLED === 'true'


router.beforeEach(async (to, from, next) => {
  const token   = getToken()
  const storeId = getStoreId()
  const meStore = useUser()
  const requiresAuth = to.matched.some(r => r.meta?.requiresAuth)

  // ログインしているのに me が未取得なら先に読み込む
  if (token && storeId && !meStore.me) {
    try { await meStore.fetchMe?.() } catch {}
  }
  const me     = meStore.me
  const claims = me?.claims || []

  // 1) ルート（'/'）はロール別ホームへ
  if (to.path === '/') {
    if (!token || !storeId) return next('/login')
    if (claims.includes('cast_order_self')) return next('/cast/mypage')
    // me がまだ無い時は一度保留（ローディング経由）でもOK。ここでは簡潔にフォールバック。
    if (claims.includes('operate_orders') || claims.includes('station_view')) return next('/dashboard')
    if (me?.is_superuser || claims.includes('view_pl_multi'))  return next('/bills/pl/daily')

    return next('/dashboard')
  }

  // 2) ログイン画面はログイン済みならホームへ
  if (to.name === 'login') {
    return next(token && storeId ? '/' : undefined)
  }

  // 3) 認証必須の保護
  if (requiresAuth && (!token || !storeId)) {
    return next({ path: '/login', query: { next: to.fullPath } })
  }

  // 4) 機能capガード
  const cap = to.meta?.cap
  if (cap && !claims.includes(cap)) return next('/403')
  // いずれかcap（PL：view_pl_store or view_pl_multi）
  const capsAny = to.meta?.capsAny
  if (Array.isArray(capsAny) && !capsAny.some(c => claims.includes(c))) {
    return next('/403')
  }

  // 5) KDSフラグ
  if (to.meta?.kds && import.meta.env.VITE_KDS_ENABLED !== 'true') return next('/')

  next()
})

export default router