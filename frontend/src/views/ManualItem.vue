<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { findSection, findItem } from '@/data/manualData'

const router = useRouter()
const route = useRoute()

const prefix = computed(() => {
  const name = route.name || ''
  return name.replace(/-manual.*/, '')
})

const section = computed(() => findSection(route.params.sectionId))
const item = computed(() => findItem(route.params.sectionId, route.params.itemId))

function sectionRoute() {
  return { name: `${prefix.value}-manual-section`, params: { sectionId: route.params.sectionId } }
}

function copyLink() {
  navigator.clipboard.writeText(window.location.href)
}
</script>

<template>
  <div class="container py-4" style="max-width: 720px;">
    <div class="d-flex align-items-center gap-2 mb-4">
      <button class="btn btn-sm btn-outline-secondary" @click="router.push(sectionRoute())">
        <IconArrowLeft :size="16" /> {{ section?.title }}
      </button>
    </div>

    <template v-if="item">
      <h4 class="fw-bold mb-4">{{ item.q }}</h4>

      <div class="card">
        <div class="card-body" style="font-size: 0.95rem; line-height: 1.8; white-space: pre-line;">{{ item.a }}</div>
      </div>

      <div class="mt-3 text-end">
        <button class="btn btn-sm btn-outline-secondary" @click="copyLink">
          <IconLink :size="14" /> このページのリンクをコピー
        </button>
      </div>
    </template>

    <div v-else class="text-muted">ページが見つかりません。</div>
  </div>
</template>
