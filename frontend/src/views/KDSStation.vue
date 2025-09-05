<!-- src/views/KDSStation.vue -->
<script setup>
import { onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useKDS } from '@/stores/useKDS'
import { kds } from '@/api'

const route = useRoute()
const station = computed(() => route.path.includes('kitchen') ? 'kitchen' : 'drinker')
const store = useKDS()

// 起動時に long-poll 開始／終了時に停止
onMounted(() => store.startLongPollTickets(station.value))
onBeforeUnmount(() => store.stopLongPollTickets())

// 既存テンプレの「更新」ボタン互換（そのまま使えるように）
store.fetchTickets = (st) => store.startLongPollTickets(st?.value ?? st)

// 操作直後はローカル反映で“リロード感”を消す
async function onAck(t)   { await kds.ack(t.id);   store.ackLocal(t.id) }
async function onReady(t) { await kds.ready(t.id); store.removeLocal(t.id) }

function fmtSec(sec){ const m=Math.floor((sec||0)/60); const ss=String((sec||0)%60).padStart(2,'0'); return `${m}:${ss}` }
</script>


<template>
  <div class="container py-3">
    <h2 class="mb-3 text-uppercase">{{ station }} KDS</h2>
    <div class="d-flex gap-2 mb-3">
      <button class="btn btn-outline-secondary btn-sm" @click="store.fetchTickets(station)">更新</button>
      <span class="text-muted">件数: {{ store.tickets.length }}</span>
    </div>

    <div class="row g-3">
      <div class="col-12 col-md-6 col-lg-4" v-for="t in store.tickets" :key="t.id">
        <div class="card shadow-sm">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <span class="badge bg-dark fs-5 p-2">卓 {{ t.table_no ?? '-' }}</span>
              <span class="badge bg-secondary">{{ t.ordered_by }}</span>
            </div>
            <div class="fw-bold fs-5 mb-1">{{ t.item_name }}</div>
            <div class="text-muted small">経過: {{ fmtSec(t.elapsed_sec ?? 0) }}</div>
            <div class="mt-3 d-flex gap-2">
              <button class="btn btn-outline-primary" @click="onAck(t)">ACK</button>
              <button class="btn btn-primary" @click="onReady(t)">READY</button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="store.tickets.length===0" class="col-12">
        <div class="alert alert-light border text-center">なし</div>
      </div>
    </div>
  </div>
</template>
