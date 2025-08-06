import BillList from '@/views/DashboardList.vue'

export default createRouter({
	history : createWebHistory(),
	routes  : [
		{ path:'/bills', component: BillList },
		
	]
})
