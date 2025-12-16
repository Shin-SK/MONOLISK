<!-- PLPage: 日・月・年のPLをタブ切り替えで表示（押された時だけmount） -->
<script setup>
import { ref } from 'vue'
import PLDaily from '@/views/BillPLDaily.vue'
import PLMonthly from '@/views/BillPLMonthly.vue'
import PLYearly from '@/views/BillPLYearly.vue'

const props = defineProps({
  storeIds: { type: Array, default: () => [] }
})

const activeTab = ref('daily') // 'daily' | 'monthly' | 'yearly'

function switchTab(tab) {
  activeTab.value = tab
}
</script>

<template>
  <nav class="row border-bottom g-1 mb-3">
    <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'daily' }">
      <button
        class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
        @click="switchTab('daily')">
        日
      </button>
    </div>
    <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'monthly' }">
      <button
        class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
        @click="switchTab('monthly')">
        月
      </button>
    </div>
    <div
      class="col-4"
      :class="{ 'border-bottom border-3 border-secondary': activeTab === 'yearly' }">
      <button
        class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
        @click="switchTab('yearly')">
        年
      </button>
    </div>
  </nav>

  <div class="pl">
    <PLDaily v-if="activeTab === 'daily'" :key="'daily'" :store-ids="storeIds" />
    <PLMonthly v-else-if="activeTab === 'monthly'" :key="'monthly'" :store-ids="storeIds" />
    <PLYearly v-else :key="'yearly'" :store-ids="storeIds" />
  </div>
</template>
