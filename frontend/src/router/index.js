import BillList from '@/views/BillList.vue'

export default createRouter({
	history : createWebHistory(),
	routes  : [
		{ path:'/bills', component: BillList },
		// …既存ルート…
	]
})
