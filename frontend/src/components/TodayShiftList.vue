<!-- src/components/TodayShiftList.vue -->
<script setup>
import { defineProps } from 'vue'
import { useTodayShiftPlans } from '@/composables/useTodayShiftPlans'

const props = defineProps({
  /* 親が渡さなければ「全店」 */
  storeId: { type: [String, Number], default: null }
})

const { list } = useTodayShiftPlans(props.storeId)
</script>

<template>
  <div class="today-shift-list">
    <h5 class="mb-3">
      今日の出勤者
    </h5>

    <template v-if="list.length">
      <ul class="list-group">
        <li
          v-for="p in list"
          :key="p.id"
          class="list-group-item d-flex align-items-center gap-2"
        >
          <img
            :src="p.photo_url || '/img/cast-default.png'"
            class="rounded-circle"
            style="width:32px;height:32px;object-fit:cover;"
            @error="$event.target.src='/img/cast-default.png'"
          >
          <span>{{ p.stage_name }}</span>
          <small class="ms-auto text-muted">{{ p.start_at }}-{{ p.end_at }}</small>
          <span
            v-if="p.is_checked_in"
            class="badge bg-success ms-2"
          >IN</span>
        </li>
      </ul>
    </template>

    <p
      v-else
      class="text-muted"
    >
      該当なし
    </p>
  </div>
</template>
