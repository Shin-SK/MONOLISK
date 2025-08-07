<script setup>
import CustomerPicker from '@/components/CustomerPicker.vue'
</script>

<template>
  <div class="container py-4">
    <h1 class="mb-4">顧客管理</h1>

    <!-- 単独ページではそのまま使える -->
    <CustomerPicker @saved="() => $toast?.success?.('保存しました')" />
  </div>
</template>
