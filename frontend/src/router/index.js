import { createRouter, createWebHistory } from 'vue-router'
import Base from '@/layouts/Base.vue'
import Login from '@/pages/Login.vue'
import Dashboard from '@/pages/Dashboard.vue'
import ReservationList from '@/pages/ReservationList.vue'
import ReservationDetail from '@/pages/ReservationDetail.vue'
import ReservationEdit from '@/pages/ReservationEdit.vue'
import ReservationCreate from '@/pages/ReservationCreate.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: Login },
  { 
    path: '/dashboard', 
    component: Base,
    children: [ // 子ルートを定義
      { path: '', component: Dashboard },
      { path: 'reservations', component: ReservationList },
      { path: 'reservations/create', component: ReservationCreate },
      { path: 'reservations/:id', component: ReservationDetail },
      { path: 'reservations/:id/edit', component: ReservationEdit }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
