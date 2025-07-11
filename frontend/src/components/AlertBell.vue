<script setup>
import { computed, defineProps } from 'vue'
import { yen } from '@/utils/money'

const props = defineProps({
  alerts   : { type: Array,  default: () => [] }, // 全履歴
  dismissed: {             // 既読 Set（Dashboard 側から）
    type   : Object,
    default: () => new Set()
  }
})

/* 未読数＝履歴－既読 */
const unread = computed(() =>
  props.alerts.filter(a => !props.dismissed.has(a.driver_id)).length
)
</script>

<template>
  <div class="dropdown">
    <!-- 鈴 -->
    <button class="btn btn-link p-0 position-relative" data-bs-toggle="dropdown">
      <i class="bi bi-bell fs-4"></i>
      <!-- 未読バッジ -->
      <span v-if="unread"
            class="position-absolute top-0 start-100 translate-middle
                   badge rounded-pill bg-danger">
        {{ unread }}
      </span>
    </button>

    <!-- 一覧ドロップダウン -->
    <ul class="dropdown-menu bg-white">
      <li v-if="!alerts.length" class="dropdown-item text-muted">
        アラートはありません
      </li>

      <li v-for="a in alerts"
          :key="a.driver_id"
          class="dropdown-item small"
          :class="{ 'text-muted': dismissed.has(a.driver_id) }">
        <div class="d-flex">
          <span class="text-muted me-2">{{ a.time }}</span>
          <span>{{ a.driver_name }} さん – {{ yen(a.cash) }} 円</span>
        </div>
      </li>
    </ul>
  </div>
</template>


<style>

.dropdown-menu{
  min-width: 260px;
    max-height: 60vh;
    overflow: auto;
    background-color: white;
    border-radius: 16px;
    border: unset;
    min-height: 200px;
    padding: 16px;
    position: absolute;
    inset: 0px auto auto 0px;
    margin: 0px;
    transform: translate(0px, 36px);
}


</style>