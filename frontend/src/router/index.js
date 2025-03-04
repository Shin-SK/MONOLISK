import { createRouter, createWebHistory } from 'vue-router'
import Base from '@/layouts/Base.vue'
import Login from '@/pages/Login.vue'
import Dashboard from '@/pages/Dashboard.vue'
import ReservationList from '@/pages/ReservationList.vue'
import ReservationDetail from '@/pages/ReservationDetail.vue'
import ReservationCreate from '@/pages/ReservationCreate.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: Login },
  { 
    path: '/dashboard', 
    component: Base,
    children: [
      { path: '', component: Dashboard },
      { path: 'reservations', component: ReservationList },
      { path: 'reservations/create', component: ReservationCreate },
      // ReservationDetail を「詳細＆編集ページ」として利用
      { path: 'reservations/:id', component: ReservationDetail },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
