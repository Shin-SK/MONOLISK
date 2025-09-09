// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App    from './App.vue'
import router from './router'
import 'bootstrap';

import ganttastic from '@infectoone/vue-ganttastic'

import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

import DatePicker from 'vue-datepicker-next'
import 'vue-datepicker-next/index.css'

import '@/assets/scss/main.scss'
import '@/plugins/dayjs'

import Avatar from '@/components/Avatar.vue' 

import { yen } from '@/utils/money'

import Sortable, { Swap } from 'sortablejs'
Sortable.mount(new Swap())

import ECharts from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
use([CanvasRenderer, LineChart, PieChart, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])


import {
	IconMenu2,
	IconPinned,
	IconList,
	IconMenu3,
	IconNotes,
	IconUsers,
	IconHistoryToggle,
	IconCurrencyYen,
	IconTrash,
	IconPlus,
	IconRefresh,
	IconLayoutDashboard,
	IconUser,
	IconUserFilled,
  IconFileNeutral,
  IconShoppingCart,
  IconReceiptYen,
  IconDeviceFloppy,
  IconX,
} from '@tabler/icons-vue'



  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)
  app.use(router)

  .use(ganttastic)
  app.config.globalProperties.$yen = yen
  app.component('Multiselect', Multiselect)  // グローバル登録
  app.component('DatePicker', DatePicker)
  app.component('Avatar', Avatar)  
  app.component('VChart', ECharts)

  // 使う分だけ登録（足りなければここに追加していく）
  const icons = {
    IconMenu2,
    IconPinned,
    IconList,
    IconMenu3,
    IconNotes,
    IconUsers,
    IconHistoryToggle,
    IconCurrencyYen,
    IconTrash,
    IconPlus,
    IconRefresh,
    IconLayoutDashboard,
    IconUser,
    IconUserFilled,
    IconFileNeutral,
    IconShoppingCart,
    IconReceiptYen,
    IconDeviceFloppy,
    IconX,
  }
  Object.entries(icons).forEach(([name, comp]) => app.component(name, comp))

  ;(async () => {
    await router.isReady()
    app.mount('#app')
  })()
