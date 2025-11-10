// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getStoreId } from '@/auth'
import { useUser } from '@/stores/useUser'

/* --- レイアウト --- */
// import MainLayout from '@/layouts/MainLayout.vue'
import CastLayout from '@/layouts/CastLayout.vue'
import StaffLayout from '@/layouts/StaffLayout.vue'
import OwnerLayout from '@/layouts/OwnerLayout.vue'
import ManagerLayout from '@/layouts/ManagerLayout.vue'

import { useRoles } from '@/composables/useRoles'


const routes = [


  {
    path: '/settings',
    component: ManagerLayout,
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
    component: StaffLayout,
    meta: { rolesAny: ['staff','manager','owner','superuser'], title: 'STAFF' },
    children: [
      { path: 'mypage', name: 'staff-mypage', component: () => import('@/views/staff/StaffMypage.vue'), meta:{ rolesAny: ['staff','manager','owner','superuser'], title:'MYPAGE' } },
      { path: 'dashboard',
        name: 'staff-dashboard',
        component: () => import('@/views/DashboardAdmin.vue'),
        meta:{ rolesAny: ['staff','manager','owner','superuser'], title:'DASHBOARD' }
      },
      { path: 'dashboard/list',
        name: 'staff-dashboard-list',
        component: () => import('@/views/DashboardList.vue'),
        meta:{ rolesAny: ['staff','manager','owner','superuser'], title:'DASHBOARD-LIST' }
      },
      { path: 'dashboard/timeline',
        name: 'staff-dashboard-timeline',
        component: () => import('@/views/DashboardGantt.vue'),
        meta:{ rolesAny: ['staff','manager','owner','superuser'], title:'DASHBOARD-TIMELINE' }
      },
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

  // ---------- マネージャー ---------- //
  {
    path: '/manager',
    component: ManagerLayout,
    meta: { rolesAny: ['manager','superuser'], title: 'MANAGER' },
    children: [
      { path: '', redirect: { name: 'mng-dashboard' } },
      { path: 'dashboard', name: 'mng-dashboard', component: () => import('@/views/manager/ManagerDashboard.vue'), meta:{ rolesAny: ['manager','superuser'], title:'DASHBOARD' } },

      { path: 'bill', name:'mng-bill-table', component: () => import('@/views/DashboardAdmin.vue'), meta: { title: 'BILL-TABLE', rolesAny: ['manager','staff' ,'superuser'], requiresAuth: true, adminOnly: true }},
      { path: '/bills/:id', name: 'BillDetail', component: () => import('@/views/BillDetailPage.vue'), props: true },
      { path: 'bill/list', name:'mng-bill-list', component: () => import('@/views/DashboardList.vue'),  meta: { title: 'BILL-LIST', rolesAny: ['manager','staff' ,'superuser'], requiresAuth: true, adminOnly: true }},
      { path: 'bill/timeline', name:'mng-bill-tl', component: () => import('@/views/DashboardGantt.vue'), meta: { title: 'BILL-TIMELINE', rolesAny: ['manager','staff' ,'superuser'], requiresAuth: true, adminOnly: true }},

      { path: 'profile', name: 'mng-profile', component: () => import('@/views/ProfileEdit.vue'), meta:{ rolesAny:['manager'], title:'プロフィール編集' } },
      { path: 'pl/daily',  name:'mng-pl-daily',  component: () => import('@/views/BillPLDaily.vue'),   meta: { title: '売上-日次', rolesAny: ['owner','superuser'], requiresAuth:true } },
      { path: 'pl/Monthly', name:'mng-pl-monthly', component: () => import('@/views/BillPLMonthly.vue'), meta: { title: '売上-月次', rolesAny: ['owner','superuser'], requiresAuth:true } },
      { path: 'pl/yearly', name:'mng-pl-yearly',  component: () => import('@/views/BillPLYearly.vue'), meta: { title: '売上-年次', rolesAny: ['owner','superuser'], requiresAuth:true } },
      
      { path: 'cast-sales', name:'mng-cast-sales', component: () => import('@/views/CastSalesList.vue'),   meta: { title: 'キャスト売上', requiresAuth: true, adminOnly: true } },
      { path: 'cast-sales/:id',    component: () => import('@/views/CastSalesDetail.vue'), props: true, name: 'cast-sales-detail', meta: { title: 'キャスト売上', requiresAuth: true, adminOnly: true } },
      { path: 'cast-shift', name:'mng-cast-shift' ,component: () => import('@/views/CastShiftList.vue'),   props: true, meta: { title: 'シフト管理' } },
      { path: 'cast-shift/:id(\\d+)/shifts', name:'mng-cast-shift-detail', component: () => import('@/views/CastShiftPage.vue'), props: true , meta: { title: 'シフト管理' } },

      { path: 'ranking', name:'mng-ranking',  component: () => import('@/views/CastRanking.vue'),        props: true, meta: { title: 'ランキング',    requiresAuth: true, adminOnly: true } },
      { path: 'table', name:'mng-tables', component: () => import('@/components/BillListTable.vue'), props: true, meta: { title: 'テーブルビュー', requiresAuth: true, adminOnly: true }},
      { path: 'customers', name:'mng-customers', component: () => import('@/views/CustomerPage.vue'),       props: true, meta: { title: '顧客情報',      requiresAuth: true, adminOnly: true }},
      { path: 'profile', name: 'mng-profile', component: () => import('@/views/ProfileEdit.vue'), meta:{ title:'プロフィール編集' } },
      {
        path: 'customers/:id(\\d+)',
        name: 'customer-detail',
        component: () => import('@/views/CustomerForm.vue'),
        props: true,
        meta: { title: '顧客編集', requiresAuth: true, adminOnly: true }
      },
      { path: 'staff/:id(\\d+)', redirect: to => ({ name: 'settings-staff-form', params: { id: to.params.id } }) },
      { path: 'staffs/new',      redirect: { name: 'settings-staff-new' } },
      { path: 'casts/:id(\\d+)', redirect: to => ({ name: 'settings-cast-form', params: { id: to.params.id } }) },
      { path: 'casts/new',       redirect: { name: 'settings-cast-new' } },
      // 給与計算
      {
        path: '/payroll',
        name: 'Payroll',
        component: () => import('@/views/PayrollPage.vue')
      },
      {
        path: '/payroll/cast/:id',
        name: 'PayrollCastDetail',
        component: () => import('@/views/PayrollCastDetail.vue'),
        props: true
      },

      {
        path: 'kds/kitchen',
        name: 'mng-kds-kitchen',
        alias: ['/kds/kitchen'],             // ← 互換
        component: () => import('@/views/KDSStation.vue'),
        meta: { title: 'KDS Kitchen', requiresAuth: true, kds: true }
      },
      {
        path: 'kds/drinker',
        name: 'mng-kds-drinker',
        alias: ['/kds/drinker'],             // ← 互換
        component: () => import('@/views/KDSStation.vue'),
        meta: { title: 'KDS Drinker', requiresAuth: true, kds: true }
      },
      {
        path: 'kds/dishup',
        name: 'mng-kds-dishup',
        alias: ['/kds/dishup'],              // ← 互換
        component: () => import('@/views/KDSDishup.vue'),
        meta: { title: 'KDS Deshap', requiresAuth: true, kds: true }
      },

    ]
  },


  // ---------- その他認証系 ---------- //
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
  { path: '/casts',     redirect: { name: 'settings-cast-list' } },
  { path: '/casts/new', redirect: { name: 'settings-cast-new' } },

  // ---------- その他 ---------- //
  {
    path: '/manual-viewer',
    name: 'manual-viewer',
    component: () => import('@/views/ManualViewer.vue'),
    meta: { layout: 'Plain' } // 任意：戻るボタンだけのレイアウト等
  },
]


// === store_id 解決ユーティリティ ===
function pickSidFromQuery(route) {
  // __sid が複数ある場合は“最後の1個”を採用
  const q = route.fullPath.split('?')[1] || ''
  const params = new URLSearchParams(q)
  const all = params.getAll('__sid')
  if (!all.length) return ''
  const last = all[all.length - 1] || ''
  const sid = last.split('-')[0].trim()
  return sid || ''
}

function stripSidFromUrl() {
  const url = new URL(window.location.href)
  // URLSearchParams.delete は同名を“すべて”削除する
  url.searchParams.delete('__sid')
  window.history.replaceState(null, '', url.toString())
}



const router = createRouter({
  history: createWebHistory(),
  routes,
})

const KDS_ENABLED = import.meta.env.VITE_KDS_ENABLED === 'true'


router.beforeEach(async (to, from, next) => {
  const token = getToken()

  // 1) __sid が来ていれば最優先で採用→localStorageへ→URLから除去
  const sidFromQuery = pickSidFromQuery(to)
  if (sidFromQuery) {
    localStorage.setItem('store_id', String(sidFromQuery))
    stripSidFromUrl()
  }

  // 2) ここで storeId を確定（以降の判定はこれを使う）
  let storeId = getStoreId()

  const meStore = useUser()
  const { hasRoleOrSuper, homePath } = useRoles()

  const roleProtected = to.matched.some(r => Array.isArray(r.meta?.rolesAny))
  const requiresAuth  = to.matched.some(r => r.meta?.requiresAuth) || roleProtected

  console.log('[guard] →', to.fullPath, { token: !!token, storeId, requiresAuth })

  // 3) 認証済み & storeIdがあるのに me 未取得なら fetch
  if ((token && storeId) && !meStore.me) {
    try {
      console.log('[guard] fetchMe start')
      await meStore.fetchMe?.()
      console.log('[guard] fetchMe done', meStore.me?.current_role, meStore.me?.current_store_id)
    } catch (e) {
      console.warn('[guard] fetchMe error', e)
    }
  }

  // 4) store_id の確定ロジック（上書きしない！）
  //    __sid > localStorage（現状）> me（保険） の順で充当
  if (!storeId) {
    const fromMe =
      (meStore.me?.current_store_id && String(meStore.me.current_store_id)) ||
      (Array.isArray(meStore.me?.stores) && meStore.me.stores[0] && String(meStore.me.stores[0].id)) ||
      ''
    if (fromMe) {
      localStorage.setItem('store_id', fromMe)
      storeId = fromMe
      console.log('[guard] store_id fallback from me ->', fromMe)
    }
  }
  // ★ ここで “me に合わせて同期上書き” はしない（今回のバグ源）

  // 5) ルートガード基本
  if (to.path === '/') {
    if (!token || !storeId) { console.log('[guard] / → login'); return next('/login') }
    const dest = homePath() || '/'
    console.log('[guard] / →', dest)
    if (to.fullPath === dest || from.fullPath === dest) return next()
    return next({ path: dest, replace: true })
  }

  if (to.name === 'login') {
    console.log('[guard] login route, token?', !!token, 'store?', !!storeId)
    return next(token && storeId ? '/' : undefined)
  }

  if (requiresAuth && (!token || !storeId)) {
    console.log('[guard] need auth → /login')
    return next({ path: '/login', query: { next: to.fullPath } })
  }

  const required = to.matched.map(r => r.meta?.rolesAny).find(a => Array.isArray(a))
  if (required && !hasRoleOrSuper(required)) {
    const dest = homePath() || '/'
    console.log('[guard] role mismatch →', dest, 'required=', required)
    if (dest === to.fullPath || dest === from.fullPath) return next()
    return next({ path: dest, replace: true })
  }

  console.log('[guard] pass')
  return next()
})



export default router