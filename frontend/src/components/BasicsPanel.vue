<!-- src/components/BasicsPanel.vue -->
<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  /** 表示切替: 'base' / 'customer'（SP用） */
  activePane: { type: String, default: 'base' },

  /** テーブル候補・現在値 */
  tables: { type: Array, default: () => [] },
  tableId: { type: [Number, null], default: null },

  /** 人数 */
  pax: { type: Number, default: 1 },

  /** セット候補（{ id, code, label } の配列） */
  courseOptions: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:tableId', 'update:pax', 'chooseCourse'])

/* セット選択は変更時に即 choose → 自動クリア */
const selectedCourse = ref(null)
watch(selectedCourse, (opt) => {
  if (!opt) return
  emit('chooseCourse', opt)
  selectedCourse.value = null
})
</script>

<template>
  <div
    class="d-flex justify-content-between flex-md-column flex-row"
    :class="{ 'd-none d-md-block': activePane !== 'base' }"
  >
    <!-- テーブル番号 -->
    <div class="wrap">
      <div class="title"><IconPinned />テーブル</div>
      <div class="items">
        <select
          class="form-select text-end"
          style="width: 80px;"
          :value="tableId"
          @change="e => emit('update:tableId', e.target.value ? Number(e.target.value) : null)"
        >
          <option class="text-center" :value="null">-</option>
          <option
            v-for="t in tables"
            :key="t.id"
            :value="t.id"
          >
            {{ t.number }}
          </option>
        </select>
      </div>
    </div>

    <!-- 人数 -->
    <div class="wrap">
      <div class="title"><IconUsers />人数</div>
      <div class="items">
        <select
          class="form-select text-center"
          style="width: 80px;"
          :value="pax"
          @change="e => emit('update:pax', Number(e.target.value))"
        >
          <option v-for="n in 12" :key="n" :value="n">{{ n }}</option>
        </select>
      </div>
    </div>

    <!-- セット（選択→即追加→クリア） -->
    <div class="wrap">
      <div class="title"><IconHistoryToggle />セット</div>
      <div class="items">
        <select
          v-model="selectedCourse"
          class="form-select"
        >
          <option :value="null">- SET -</option>
          <option
            v-for="c in courseOptions"
            :key="c.id"
            :value="c"
          >
            {{ c.label }}
          </option>
        </select>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrap { margin-bottom: .5rem; }
.title { font-weight: 600; display: flex; align-items: center; gap: .4rem; }
.items { margin-top: .25rem; }
</style>
