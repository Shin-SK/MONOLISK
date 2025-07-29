<script setup>
import { yen } from '@/utils/money'
defineProps({ rows: { type: Array, required: true } })
</script>

<template>
  <table class="table table-striped w-100">
    <thead class="table-dark">
      <tr><th>#</th><th>キャスト</th><th class="text-end">小計</th></tr>
    </thead>
    <tbody>
      <tr v-for="(r,i) in rows" :key="r.cast_id">
        <td>{{ i+1 }}</td>
        <td>{{ r.stage_name }}</td>
        <td class="text-end">{{ yen(r.revenue) }}</td>
      </tr>
    </tbody>
  </table>
</template>
