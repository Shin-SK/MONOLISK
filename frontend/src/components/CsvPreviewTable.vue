<!-- src/components/CsvPreviewTable.vue -->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  headers: {
    type: Array,
    required: true,
  },
  rows: {
    type: Array,
    default: () => [],
  },
  maxRows: {
    type: Number,
    default: 20,
  },
})

const displayRows = computed(() => {
  return props.rows.slice(0, props.maxRows)
})

const hasMore = computed(() => {
  return props.rows.length > props.maxRows
})
</script>

<template>
  <div class="csv-preview-table">
    <div v-if="!rows.length" class="text-center text-muted py-3">
      データがありません
    </div>
    <div v-else class="table-responsive">
      <table class="table table-sm table-striped table-bordered">
        <thead>
          <tr>
            <th v-for="h in headers" :key="h">{{ h }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in displayRows" :key="i">
            <td v-for="h in headers" :key="h">
              {{ String(row[h] ?? '') }}
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="hasMore" class="text-muted small text-center py-2">
        残り {{ rows.length - maxRows }} 行（ダウンロードで全件取得できます）
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.csv-preview-table {
  max-height: 400px;
  overflow-y: auto;
  
  table {
    font-size: 0.875rem;
    margin-bottom: 0;
    
    th, td {
      white-space: nowrap;
      padding: 0.5rem;
    }
  }
}
</style>
