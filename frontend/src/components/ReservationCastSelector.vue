<script setup>
/* =============================================================
 *  ReservationCastSelector.vue
 * -------------------------------------------------------------
 *  props
 *  -----
 *    casts       : 表示させるキャスト一覧
 *    modelValue  : 選択中キャスト ID 配列（v‑model）
 *
 *  emit
 *  ----
 *    update:modelValue : チェックトグル時に発火
 *
 *  役割は UI のみ。API 通信や店舗フィルタリングは親側に委譲。
 * ============================================================= */

const props = defineProps({
  casts: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

function toggle(id) {
  const next = props.modelValue.includes(id)
    ? props.modelValue.filter(x => x !== id)
    : [...props.modelValue, id]
  emit('update:modelValue', next)
}
</script>

<template>
  <div class="d-flex flex-wrap gap-3" role="group" aria-label="Casts">
    <template v-for="c in casts" :key="c.id">
      <!-- hidden checkbox (Bootstrap の btn-check を流用) -->
      <input class="btn-check" type="checkbox"
             :id="`cast-${c.id}`"
              :checked="modelValue.includes(Number(c.id))"
              @change="toggle(Number(c.id))">

      <!-- 表示用ボタン -->
      <label class="btn btn-outline-primary d-flex align-items-center gap-2"
             :class="{ active: modelValue.includes(c.id) }"
             :for="`cast-${c.id}`">
        <img :src="c.photo_url || '/static/img/cast-default.png'"
             class="rounded-circle border"
             style="width:32px;height:32px;object-fit:cover;">
        <span>{{ c.stage_name }}（☆{{ c.star_count }}）</span>
      </label>
    </template>
  </div>
</template>
