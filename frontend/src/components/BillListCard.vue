<script setup>
import { computed } from 'vue'
import dayjs from 'dayjs'
import Avatar from '@/components/Avatar.vue'

const props = defineProps({
  bill: {
    type: Object,
    required: true
  },
  isSelectable: {
    type: Boolean,
    default: false
  },
  isSelected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select', 'edit'])

function calcPax(b) {
  if (!b) return 0
  const items = b.items || []
  let total = 0
  for (const it of items) {
    const code = it.item_master?.code || it.code || ''
    if (code.includes('Male') || code.includes('Female')) {
      total += (it.qty || 0)
    }
  }
  return total
}

function liveCasts(b) {
  const map = new Map();

  (b.stays || []).forEach(s => {
    const id = s.cast?.id
    if (!id) return

    const present = !s.left_at
    const entered = new Date(s.entered_at).getTime()

    const prev = map.get(id)
    if (
      !prev ||
      (present && !prev.present) ||
      entered > prev.entered
    ) {
      map.set(id, { stay: s, present, entered })
    }
  })

  return [...map.values()].map(({ stay, present }) => ({
    id: stay.cast?.id,
    name: stay.cast?.stage_name || "N/A",
    avatar: stay.cast?.avatar_url || "/img/user-default.png",
    color: stay.stay_type === "nom" ? "danger"
         : stay.stay_type === "in" ? "success"
         : stay.stay_type === "dohan" ? "secondary"
         : "blue",
    present
  }))
}

function hasMemo(b) {
  return !!(b?.memo && String(b.memo).trim())
}

function handleSelect(e) {
  e.stopPropagation()
  emit('select', props.bill.id)
}

function handleEdit(e) {
  e.stopPropagation()
  emit('edit', props.bill.id)
}
</script>

<template>
  <div
    class="card bill-card"
    :class="{ 'selected': isSelected }"
  >
    <!-- チェックボックス（選択モード時のみ表示） -->
    <div v-if="isSelectable" class="card-checkbox">
      <input
        type="checkbox"
        :checked="isSelected"
        @change="handleSelect"
      />
    </div>

    <div class="card-header">
      <div class="row g-2">
        <div class="col">
          <div class="label">卓番号</div>
          <div class="value">{{ bill.table?.number ?? '-' }}</div>
        </div>
        <div class="col">
          <div class="label">開始</div>
          <div class="value">{{ bill.opened_at ? dayjs(bill.opened_at).format('HH:mm') : '-' }}</div>
        </div>
        <div class="col">
          <div class="label">終了</div>
          <div class="value">{{ bill.closed_at ? dayjs(bill.closed_at).format('HH:mm') : (bill.expected_out ? dayjs(bill.expected_out).format('HH:mm') : '-') }}</div>
        </div>
        <div class="col">
          <div class="label">延長</div>
          <div class="value">{{ bill.ext_minutes ? Math.floor(bill.ext_minutes / 30) : '-' }}</div>
        </div>
        <div class="col">
          <div class="label">人数</div>
          <div class="value">{{ calcPax(bill) || '-' }}</div>
        </div>
        <div class="col">
          <div class="label">SET数</div>
          <div class="value">{{ bill.set_rounds || '-' }}</div>
        </div>
      </div>
    </div>

    <div class="card-body">
      <!-- キャスト表示 -->
      <div class="casts-section">
        <!-- 今ついているキャスト -->
        <div class="d-flex flex-wrap gap-2 mb-2">
          <div
            v-for="p in liveCasts(bill).filter(p => p.present)"
            :key="p.id"
            class="d-flex align-items-center badge text-light p-2"
            :class="`bg-${p.color}`"
          >
            <Avatar
              :url="p.avatar"
              :alt="p.name"
              :size="16"
              class="me-1"
            />
            <span class="fw-bold">{{ p.name }}</span>
          </div>
        </div>

        <!-- 過去に付いたキャスト -->
        <div class="d-flex flex-wrap gap-1">
          <span
            v-for="p in liveCasts(bill).filter(p => !p.present)"
            :key="p.id"
            class="badge bg-secondary-subtle text-dark small"
          >
            {{ p.name }}
          </span>
        </div>
      </div>
    </div>

    <div class="card-footer">
      <div class="row g-2">
        <div class="col-6">
          <div class="label">小計</div>
          <div class="value">¥{{ bill.subtotal?.toLocaleString() || '-' }}</div>
        </div>
        <div class="col-6">
          <div class="label">合計</div>
          <div class="value">¥{{ (bill.settled_total ?? (bill.closed_at ? bill.total : bill.grand_total))?.toLocaleString() || '-' }}</div>
        </div>
        <div class="col-12">
          <div class="label">メモ</div>
          <div v-if="hasMemo(bill)" class="memo-content">{{ bill.memo }}</div>
          <div v-else class="text-muted small">メモなし</div>
        </div>
      </div>

      <!-- アクション（選択モード時は非表示） -->
      <div v-if="!isSelectable" class="card-actions mt-3 d-flex gap-2">
        <button
          class="btn btn-sm btn-secondary flex-grow-1 d-flex align-items-center justify-content-center gap-1"
          @click="handleEdit"
        >
          <IconPencil />編集
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.bill-card {
  position: relative;
  border: 1px solid #ddd;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;

  &.selected {
    border-color: #0d6efd;
    background-color: #f0f6ff;
    box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.25);
  }

  &.closed::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.3);
    pointer-events: none;
    border-radius: inherit;
  }
}

.card-checkbox {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 10;
  input[type="checkbox"] {
    cursor: pointer;
    width: 20px;
    height: 20px;
  }
}

.card-header {
  background-color: white;
  .col {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
  }
}

.card-body {
  padding: 1rem;
}

.card-footer {
  border-top: 1px solid #e9ecef;
  background-color: white;
  padding: 1rem;
}

.label {
  font-size: 0.75rem;
  color: #666;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}

.value {
  font-size: 1.25rem;
  font-weight: bold;
  color: #333;
}

.casts-section {
}

.memo-content {
  white-space: pre-wrap;
  word-break: break-word;
  padding: 0.5rem;
  background-color: #f9f9f9;
  border-radius: 4px;
  font-size: 0.875rem;
}

.card-actions {
  button {
    &:hover {
      opacity: 0.85;
    }
  }
}
</style>
