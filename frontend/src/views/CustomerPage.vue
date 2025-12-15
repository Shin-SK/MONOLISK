<!-- src/views/CustomerPage.vue -->
<script setup>
import { ref } from 'vue'
import CustomerPicker from '@/components/CustomerPicker.vue'
import CustomerList from '@/views/CustomerList.vue' // 置き場所に合わせて調整

// タブ状態
const activeTab = ref('list')
const setTab = (k) => { activeTab.value = k }
// 保存後の一覧再取得トリガー
const listReloadTs = ref(0)
const lastSavedCustomer = ref(null)
const onSaved = (cust) => {
  // トーストがあれば表示
  try { window.$toast?.success?.('保存しました') } catch {}
  // 一覧に反映させるためのトリガー更新
  listReloadTs.value = Date.now()
  // 直近保存データを渡す
  lastSavedCustomer.value = cust || null
}
</script>

<template>
  <div class="py-4">

    <!-- シンプルなタブ -->
    <nav class="row border-bottom g-1 mb-3">
      <div
        class="col-6"
        :class="{ 'border-bottom border-3 border-secondary': activeTab === 'list' }">
        <button
          type="button"
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="setTab('list')"
        >
          顧客一覧
        </button>
      </div>
      <div
        class="col-6"
        :class="{ 'border-bottom border-3 border-secondary': activeTab === 'search' }">
        <button
          type="button"
          class="btn flex-grow-1 border-0 rounded-0 w-100 px-0"
          @click="setTab('search')"
        >
          検索 / 編集
        </button>
      </div>
    </nav>

    <div v-if="activeTab === 'search'">
      <CustomerPicker @saved="onSaved" />
    </div>
    <div v-else-if="activeTab === 'list'">
      <CustomerList :reload-ts="listReloadTs" :last-saved="lastSavedCustomer" />
    </div>
  </div>
</template>
