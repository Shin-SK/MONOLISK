<!-- src/views/CustomerPage.vue -->
<script setup>
import { ref } from 'vue'
import CustomerPicker from '@/components/CustomerPicker.vue'
import CustomerList from '@/views/CustomerList.vue' // 置き場所に合わせて調整

// タブ状態
const activeTab = ref('search')
const setTab = (k) => { activeTab.value = k }
</script>

<template>
  <div class="py-4">

    <!-- シンプルなタブ -->
    <nav class="nav nav-pills gap-2 mb-3">
      <button
        type="button"
        class="btn"
        :class="activeTab === 'search' ? 'btn-dark' : 'btn-outline-dark'"
        @click="setTab('search')"
      >
        顧客検索
      </button>
      <button
        type="button"
        class="btn"
        :class="activeTab === 'list' ? 'btn-dark' : 'btn-outline-dark'"
        @click="setTab('list')"
      >
        顧客一覧
      </button>
    </nav>

    <div v-if="activeTab === 'search'">
      <CustomerPicker @saved="() => $toast?.success?.('保存しました')" />
    </div>
    <div v-else-if="activeTab === 'list'">
      <CustomerList />
    </div>
  </div>
</template>
