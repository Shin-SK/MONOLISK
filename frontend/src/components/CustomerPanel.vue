<!-- src/components/CustomerPanel.vue -->
<script setup>
const props = defineProps({
  /** 表示切替: 'base' / 'customer'（SP用） */
  activePane: { type: String, default: 'base' },

  /** 選択済み顧客ID配列 */
  customerIds: { type: Array, default: () => [] },

  /** 関数を親から透過（ロジックは親に残す） */
  getLabel: { type: Function, required: true },   // (id) => label
  open:     { type: Function, required: true },   // open(id?)
  clear:    { type: Function, required: true },   // clear(id)
})
</script>

<template>
  <div class="wrap" :class="{ 'd-none d-md-block': activePane !== 'customer' }">
    <div class="title position-relative">
      <IconUserScan />顧客
      <div
        class="position-absolute top-0 bottom-0 end-0 margin-auto p-1"
        role="button"
        @click="open()"
        aria-label="顧客検索"
        title="顧客検索"
      >
        <IconSearch :size="16" />
      </div>
    </div>

    <div class="items">
      <div v-if="customerIds.length" class="d-flex flex-wrap gap-2">
        <div v-for="cid in customerIds" :key="cid">
          <IconX :size="12" role="button" class="me-2" @click.stop="clear(cid)" />
          <span @click="open(cid)" style="cursor:pointer;">
            {{ getLabel(cid) }}
          </span>
        </div>
      </div>
      <div v-else class="text-muted small">未選択</div>
    </div>
  </div>
</template>

<style scoped>
.wrap { margin-bottom: .5rem; }
.title { font-weight: 600; display: flex; align-items: center; gap: .4rem; }
.items { margin-top: .25rem; }
</style>
