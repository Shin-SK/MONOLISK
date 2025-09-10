<!-- App.vue -->
<script setup>
import SidebarOffcanvas from '@/components/SidebarOffcanvas.vue'
</script>

<template>
  <SidebarOffcanvas />

  <!-- ★ここではトランジションも Loader も持たせない -->
  <RouterView />
  <div class="cr">
    MONOLISK
  </div>
</template>
