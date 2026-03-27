<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { manualSections } from '@/data/manualData'

const router = useRouter()
const route = useRoute()

// ルート名のプレフィックスを抽出 (例: 'mng-manual' → 'mng')
const prefix = computed(() => {
  const name = route.name || ''
  return name.replace(/-manual.*/, '')
})

function sectionRoute(sectionId) {
  return { name: `${prefix.value}-manual-section`, params: { sectionId } }
}
</script>

<template>
  <div class="container py-4" style="max-width: 720px;">
    <div class="d-flex align-items-center gap-2 mb-4">
      <button class="btn btn-sm btn-outline-secondary" @click="router.back()">
        <IconArrowLeft :size="16" /> 戻る
      </button>
      <h4 class="mb-0 fw-bold">操作マニュアル</h4>
    </div>

    <p class="text-muted mb-4">困ったときはここから探してください。</p>

    <div class="d-flex flex-column gap-3">
      <router-link
        v-for="section in manualSections"
        :key="section.id"
        :to="sectionRoute(section.id)"
        class="card text-decoration-none text-body section-card"
      >
        <div class="card-body d-flex justify-content-between align-items-center">
          <div>
            <div class="fw-bold fs-5">{{ section.title }}</div>
            <div class="text-muted small mt-1">{{ section.description }}</div>
            <div class="text-muted small mt-1">{{ section.items.length }}件</div>
          </div>
          <IconChevronRight :size="20" class="text-muted" />
        </div>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.section-card {
  transition: box-shadow 0.15s;
}
.section-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
</style>
