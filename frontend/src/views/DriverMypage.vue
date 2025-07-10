<!-- src/views/DriverTimeline.vue -->
<script setup>
import { ref }             from 'vue'
import dayjs               from 'dayjs'

import TimelineView        from '@/components/TimelineView.vue'
import TaskListView        from '@/components/TaskListView.vue'

const selectedDate = ref( dayjs().toDate() ) 


</script>

<template>
  <component
    :is="$route.query.view === 'list' ? TaskListView : TimelineView"
    api-path="reservations/mine-driver/"
    detail-route="/driver/reservations"
    :show-settled="true"
    :selected-date="selectedDate"
    @date-change="d => selectedDate.value = d.toDate()"
  />
</template>
