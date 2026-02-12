<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 単一選択: Number|null
  // 複数選択: Number[]
  modelValue: { type: [Number, Array, null], default: null },

  // true: 複数選択（トグル）
  // false: 単一選択
  multiple: { type: Boolean, default: false },

  // BasicsPanel側で持ってるテーブル一覧を渡す想定
  tables: { type: Array, default: () => [] },

  // 表示対象の絞り込み済み配列を渡してもOK
  // （tables を渡した上で filteredTables を渡す運用でも良い）
  disabled: { type: Boolean, default: false },

  // Bootstrapの列クラス（3列なら col-4）
  colClass: { type: String, default: 'col-4' },

  // 表示ラベル（number/nameどっちを出すか）
  labelKey: { type: String, default: 'number' }
})

const emit = defineEmits(['update:modelValue'])

const normalizedSelectedIds = computed(() => {
  if (props.multiple) return Array.isArray(props.modelValue) ? props.modelValue : []
  return props.modelValue == null ? [] : [Number(props.modelValue)]
})

const isSelected = (id) => normalizedSelectedIds.value.includes(Number(id))

const labelOf = (t) => {
  const v = t?.[props.labelKey]
  return v != null && v !== '' ? String(v) : String(t?.name ?? t?.number ?? t?.id ?? '')
}

const toggle = (id) => {
  if (props.disabled) return
  const tid = Number(id)

  if (props.multiple) {
    const cur = Array.isArray(props.modelValue) ? props.modelValue.map(Number) : []
    const next = cur.includes(tid) ? cur.filter(x => x !== tid) : [...cur, tid]
    emit('update:modelValue', next)
    return
  }

  emit('update:modelValue', tid)
}

const sortedTables = computed(() => {
  const arr = [...props.tables]
  return arr.sort((a, b) => String(labelOf(a)).localeCompare(String(labelOf(b))))
})
</script>

<template>
  <div class="row g-1">
    <div v-for="t in sortedTables" :key="t.id" :class="colClass">
      <button
        type="button"
        class="btn w-100"
        :class="isSelected(t.id) ? 'btn-secondary' : 'btn-outline-secondary'"
        :disabled="disabled"
        @click="toggle(t.id)"
      >
        {{ labelOf(t) }}
      </button>
    </div>
  </div>
</template>
