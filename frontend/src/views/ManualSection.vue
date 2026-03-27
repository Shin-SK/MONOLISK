<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { findSection } from '@/data/manualData'

const router = useRouter()
const route = useRoute()

const prefix = computed(() => {
  const name = route.name || ''
  return name.replace(/-manual.*/, '')
})

const section = computed(() => findSection(route.params.sectionId))

function manualTop() {
  return { name: `${prefix.value}-manual` }
}
function itemRoute(itemId) {
  return { name: `${prefix.value}-manual-item`, params: { sectionId: route.params.sectionId, itemId } }
}
</script>

<template>
  <div class="container py-4" style="max-width: 720px;">
    <div class="d-flex align-items-center gap-2 mb-4">
      <button class="btn btn-sm btn-outline-secondary" @click="router.push(manualTop())">
        <IconArrowLeft :size="16" /> マニュアル
      </button>
      <h4 class="mb-0 fw-bold">{{ section?.title }}</h4>
    </div>

    <template v-if="section">
      <div class="d-flex flex-column gap-2">
        <router-link
          v-for="item in section.items"
          :key="item.id"
          :to="itemRoute(item.id)"
          class="card text-decoration-none text-body item-card"
        >
          <div class="card-body d-flex justify-content-between align-items-center py-3">
            <span class="fw-semibold">{{ item.q }}</span>
            <IconChevronRight :size="18" class="text-muted flex-shrink-0" />
          </div>
        </router-link>
      </div>
    </template>

    <div v-else class="text-muted">ページが見つかりません。</div>
  </div>
</template>

<style scoped>
.item-card {
  transition: box-shadow 0.15s;
}
.item-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
</style>
