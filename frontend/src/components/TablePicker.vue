<template>
  <div class="table-picker">
    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="table-list">
      <label v-for="table in sortedTables" :key="table.id" class="table-checkbox">
        <input
          type="checkbox"
          :value="table.id"
          :checked="modelValue.includes(table.id)"
          :disabled="disabled"
          @change="handleChange"
        />
        <span>{{ table.name }}</span>
      </label>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchTables } from '@/composables/useTables.js'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const tables = ref([])
const loading = ref(false)
const error = ref(null)

const sortedTables = computed(() => {
  return [...tables.value].sort((a, b) => (a.name || a.number || '').localeCompare(b.name || b.number || ''))
})

const handleChange = (e) => {
  const tableId = parseInt(e.target.value)
  const newValue = e.target.checked
    ? [...props.modelValue, tableId]
    : props.modelValue.filter(id => id !== tableId)
  emit('update:modelValue', newValue)
}

onMounted(async () => {
  try {
    loading.value = true
    tables.value = await fetchTables()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.table-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 0.5rem;
}

.loading,
.error {
  padding: 0.5rem;
}

.error {
  color: #d32f2f;
}

.table-list {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.table-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.table-checkbox input {
  cursor: pointer;
}

.table-checkbox input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.table-checkbox span {
  font-weight: 500;
}
</style>
