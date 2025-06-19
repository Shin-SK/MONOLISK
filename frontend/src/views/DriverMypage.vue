<!-- src/views/DriverTimeline.vue -->
<script setup>
import { ref }             from 'vue'
import dayjs               from 'dayjs'

import TimelineView        from '@/components/TimelineView.vue'
import TaskListView        from '@/components/TaskListView.vue'

/* 選択日を親 (Layout) と同期したいなら props/emit にしても良い */
const selectedDate = ref(dayjs())
</script>

<template>
  <component
    :is="$route.query.view === 'list' ? TaskListView : TimelineView"
    api-path="reservations/mine-driver/"
    detail-route="/driver/reservations"
    :show-settled="true"
    :selected-date="selectedDate"
    @date-change="d => selectedDate = d"
  />
</template>
