<!-- src/views/settings/ReleaseNotes.vue -->
<script setup>
import { ref, onMounted } from 'vue'

const notes = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/release-notes.json')
    notes.value = await res.json()
  } catch (e) {
    console.warn('release-notes.json の読み込みに失敗', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h5 class="mb-3">リリースノート</h5>

    <div v-if="loading" class="text-muted">読み込み中...</div>

    <div v-else-if="!notes.length" class="text-muted">リリースノートはありません</div>

    <div v-else class="d-flex flex-column gap-3">
      <div v-for="n in notes" :key="n.version" class="card">
        <div class="card-body">
          <div class="d-flex align-items-baseline gap-2 mb-2">
            <span class="badge bg-secondary">v{{ n.version }}</span>
            <small class="text-muted">{{ n.date }}</small>
          </div>
          <ul class="mb-0 ps-3">
            <li v-for="(c, i) in n.changes" :key="i" class="small">{{ c }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
