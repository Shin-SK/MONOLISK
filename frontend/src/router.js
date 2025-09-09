// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getStoreId } from '@/auth'
import { useUser } from '@/stores/useUser'

/* --- レイアウト --- */
import MainLayout from '@/layouts/MainLayout.vue'
import CastLayout from '@/layouts/CastLayout.vue'
import OwnerLayout from '@/layouts/OwnerLayout.vue'

import { useRoles } from '@/composables/useRoles'

// （必要なら）import { useLoading } from '@/stores/useLoading'

const routes = [
  // ---------- キャバクラ版 ---------- //
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true, adminOnly: true },
    children: [
      { path: 'dashboard',            component: () => import('@/views/DashboardAdmin.vue'), meta: { title: 'DASHBOARD', rolesAny: ['manager','staff' ,'superuser'], requiresAuth: true, adminOnly: true }},
      { path: 'dashboard/list',       component: () => import('@/views/DashboardList.vue'),  meta: { title: 'DASHBOARD-LIST', rolesAny: ['manager','staff' ,'superuser'], requiresAuth: true, adminOnly: true }},
      { path: 'dashboard/timeline',   component: () => import('@/views/DashboardGantt.vue'), meta: { title: 'DASHBOARD-TIMELINE', rolesAny: ['manager','staff' ,'superuser'], requiresAuth: true, adminOnly: true }},

      { path: '', component: () => import('@/views/DashboardList.vue'), meta: { title: '伝票' }},

      { path: 'pl/daily',  name:'pl-daily',  component: () => import('@/views/BillPLDaily.vue'),   meta: { title: '売上-日次', rolesAny: ['manager','owner','superuser'], requiresAuth:true } },
      { path: 'pl/Monthly', name:'pl-monthly', component: () => import('@/views/BillPLMonthly.vue'), meta: { title: '売上-月次', rolesAny: ['manager','owner','superuser'], requiresAuth:true } },
      { path: 'pl/yearly', name:'pl-yearly',  component: () => import('@/views/BillPLYearly.vue'), meta: { title: '売上-年次', rolesAny: ['manager','owner','superuser'], requiresAuth:true } },

      { path: 'cast-sales',           component: () => import('@/views/CastSalesList.vue'),   meta: { title: 'キャスト売上', requiresAuth: true, adminOnly: true } },
      { path: 'cast-sales/:id',       component: () => import('@/views/CastSalesDetail.vue'), props: true, name: 'cast-sales-detail', meta: { title: 'キャスト売上', requiresAuth: true, adminOnly: true } },
      { path: 'cast-shift',            component: () => import('@/views/CastShiftList.vue'),   props: true, meta: { title: 'シフト管理' } },
      { path: 'cast-shift/:id(\\d+)/shifts', component: () => import('@/views/CastShiftPage.vue'), props: true ,name: 'cast-shift-page', meta: { title: 'シフト管理' } },

      { path: 'ranking',   component: () => import('@/views/CastRanking.vue'),        props: true, meta: { title: 'ランキング',    requiresAuth: true, adminOnly: true } },
      { path: 'table',     component: () => import('@/components/BillListTable.vue'), props: true, meta: { title: 'テーブルビュー', requiresAuth: true, adminOnly: true }},
      { path: 'customers', component: () => import('@/views/CustomerPage.vue'),       props: true, meta: { title: '顧客情報',      requiresAuth: true, adminOnly: true }},

      { path: 'staff/:id(\\d+)', redirect: to => ({ name: 'settings-staff-form', params: { id: to.params.id } }) },
      { path: 'staffs/new',      redirect: { name: 'settings-staff-new' } },
      { path: 'casts/:id(\\d+)', redirect: to => ({ name: 'settings-cast-form', params: { id: to.params.id } }) },
      { path: 'casts/new',       redirect: { name: 'settings-cast-new' } },
      // 追加：KDSルート
      { path: 'kds/kitchen', component: () => import('@/views/KDSStation.vue'), meta: { title: 'KDS Kitchen', requiresAuth: true, kds: true } },
      { path: 'kds/drinker', component: () => import('@/views/KDSStation.vue'), meta: { title: 'KDS Drinker', requiresAuth: true, kds: true } },
      { path: 'kds/dishup',  component: () => import('@/views/KDSDishup.vue'),  meta: { title: 'KDS Deshap',  requiresAuth: true, kds: true } },

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
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/cast/mypage' },
      { path: 'mypage', name: 'cast-mypage' , component: () => import('@/views/cast/Mypage.vue') },
      { path: 'mypage/:id(\\d+)', redirect: { name:'cast-mypage' } },
      { path: 'order',  component: () => import('@/views/cast/Order.vue'), meta: { rolesAny: ['cast'] } },
      { path: 'profile', name: 'cast-profile', component: () => import('@/views/ProfileEdit.vue'), meta:{ rolesAny:['cast'], title:'プロフィール編集' } },
      { path: 'news/:id(\\d+)', name: 'news-detail', component: () => import('@/views/NewsDetail.vue') },
    ],
  },
  // ---------- スタッフ ---------- //
  {
    path: '/staff',
    component: MainLayout,
    meta: { rolesAny: ['staff','manager','owner','superuser'], title: 'STAFF' },
    children: [
      { path: 'mypage', name: 'staff-mypage', component: () => import('@/views/staff/StaffMypage.vue'), meta:{ rolesAny: ['staff','manager','owner','superuser'], title:'MYPAGE' } },
      { path: 'profile', name: 'staff-profile', component: () => import('@/views/ProfileEdit.vue'), meta:{ rolesAny:['staff'], title:'プロフィール編集' } },
    ]
  },
  // ---------- オーナー ---------- //
  {
    path: '/owner',
    component: OwnerLayout,
    meta: { rolesAny: ['owner','superuser'], title: 'OWNER' },
    children: [
      { path: '', redirect: { name: 'owner-dashboard' } },
      { path: 'dashboard', name: 'owner-dashboard', component: () => import('@/views/owner/OwnerDashboard.vue'), meta:{ rolesAny: ['owner','superuser'], title:'DASHBOARD' } },
      { path: 'pl/daily',  name:'owner-pl-daily',  component: () => import('@/views/BillPLDaily.vue'),   meta: { title: '売上-日次', rolesAny: ['owner','superuser'], requiresAuth:true } },
      { path: 'pl/Monthly', name:'owner-pl-monthly', component: () => import('@/views/BillPLMonthly.vue'), meta: { title: '売上-月次', rolesAny: ['owner','superuser'], requiresAuth:true } },
      { path: 'pl/yearly', name:'owner-pl-yearly',  component: () => import('@/views/BillPLYearly.vue'), meta: { title: '売上-年次', rolesAny: ['owner','superuser'], requiresAuth:true } },
      { path: 'profile', name: 'owner-profile', component: () => import('@/views/ProfileEdit.vue'), meta:{ rolesAny:['owner'], title:'プロフィール編集' } },
    ]
  },



  // ---------- その他認証系 ---------- //
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },

  { path: '/casts',     redirect: { name: 'settings-cast-list' } },
  { path: '/casts/new', redirect: { name: 'settings-cast-new' } },
]

// --- ここから下を router.js の末尾に置き換え ---

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const KDS_ENABLED = import.meta.env.VITE_KDS_ENABLED === 'true'


// 末尾の beforeEach を全置換
router.beforeEach(async (to, from, next) => {
	const token   = getToken()
	const storeId = getStoreId()
	const meStore = useUser()

	// rolesAny が一つでもあれば実質“保護画面”
	const roleProtected = to.matched.some(r => Array.isArray(r.meta?.rolesAny))

	// me 未ロード時は取得（homePath判定用）
	if ((token && storeId) && !meStore.me) {
		try { await meStore.fetchMe?.() } catch {}
	}
	const { hasRole, homePath } = useRoles()

	// 1) ルート：安全ホームへ（no-op/replace）
	if (to.path === '/') {
		if (!token || !storeId) return next('/login')
		const dest = homePath() || '/'
		if (to.fullPath === dest || from.fullPath === dest) return next()
		return next({ path: dest, replace: true })
	}

	// 2) ログイン：済ならホームへ
	if (to.name === 'login') {
		return next(token && storeId ? '/' : undefined)
	}

	// 3) 認証・store 必須（requiresAuth or rolesAny）
	const requiresAuth = to.matched.some(r => r.meta?.requiresAuth) || roleProtected
	if (requiresAuth && (!token || !storeId)) {
		return next({ path: '/login', query: { next: to.fullPath } })
	}

	// 4) 役割ガード（no-op/replaceでループ防止）
	const requiredRoles = to.matched.map(r => r.meta?.rolesAny).find(a => Array.isArray(a))
	if (requiredRoles && !hasRole(requiredRoles)) {
		const dest = homePath() || '/'
		if (dest === to.fullPath || dest === from.fullPath) return next()
		return next({ path: dest, replace: true })
	}

	// 5) KDSフラグ
	if (to.meta?.kds && import.meta.env.VITE_KDS_ENABLED !== 'true') {
		return next('/')
	}

	return next()
})



export default router