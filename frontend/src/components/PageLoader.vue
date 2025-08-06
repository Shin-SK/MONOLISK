<!-- src/components/PageLoader.vue -->
<template>
  <!-- 親を relative にすればココがピッタリ覆う -->
  <div class="loader-backdrop">
    <span class="spinner-border text-primary" />
  </div>
</template>

<style scoped>
.loader-backdrop{
  position:absolute;           /* ← fixed → absolute に変更 */
  inset:0;                     /* 親の矩形いっぱい */
  display:flex; align-items:center; justify-content:center;
  background:rgba(255,255,255,.6);   /* うす白で OK */
  z-index:20;                  /* ヘッダーより下・コンテンツより上 */
}
</style>
