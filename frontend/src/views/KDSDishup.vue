<!-- src/views/KDSDishup.vue -->
<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useKDS } from '@/stores/useKDS'
import { kds } from '@/api'

const s = useKDS()
const staffs = ref([])
const history = ref([])

// ── 小さくビープ（単一AudioContext + クールダウン） ──
let audioCtx = null
let lastBeep = 0
function beep() {
  const now = Date.now()
  if (now - lastBeep < 400) return  // 0.4sクールダウン
  lastBeep = now
  try {
    const AC = window.AudioContext || window.webkitAudioContext
    audioCtx = audioCtx || new AC()
    audioCtx.resume?.()
    const o = audioCtx.createOscillator()
    const g = audioCtx.createGain()
    o.type = 'sine'; o.frequency.value = 880
    o.connect(g); g.connect(audioCtx.destination)
    g.gain.setValueAtTime(0.0001, audioCtx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.15, audioCtx.currentTime + 0.01)
    o.start()
    o.stop(audioCtx.currentTime + 0.12)
  } catch {}
}

// 今日の履歴
async function loadHistory(){ try { history.value = await kds.historyToday(50) } catch { history.value = [] } }

// スタッフ一覧
async function loadStaffs() {
  try {
    const raw = await kds.staffList({ active: 1 })
    const arr = Array.isArray(raw?.results) ? raw.results : (Array.isArray(raw) ? raw : [])
    staffs.value = arr.map(st => ({
      id  : st.id ?? st.user?.id ?? st.pk,
      name: st.name ?? st.display_name ?? st.username ?? st.user?.username ?? `ID:${st.id ?? st.user?.id}`,
    })).filter(st => st.id)
  } catch { staffs.value = [] }
}

// 手動更新
async function load() {
  await loadStaffs()
  try { s.readyList = await kds.readyList() } catch {}
  s.readyIds = new Set(s.readyList.map(x => x.id))   // ★ 初期同期
  await loadHistory()
}

// READY新着でbeep（初回ロードでは鳴らさない）
const initialized = ref(false)
watch(() => s.readyList.length, (len, old) => {
  if (initialized.value && len > (old ?? 0)) beep()
  if (!initialized.value) initialized.value = true
})

// 初期ロード → long-poll開始
onMounted(async () => {
  await load()
  s.startLongPollReady()
})
onBeforeUnmount(() => s.stopLongPollReady())

// 『持ってく』→ 即アーカイブ + 履歴更新
async function take(ticketId, staffId){
  await kds.take(ticketId, staffId)
  s.removeReadyLocal(ticketId)
  await loadHistory()
}

// 表示用
function staffLabel(x){ return x.name }
function fmtSec(sec){ const m=Math.floor((sec||0)/60); const ss=String((sec||0)%60).padStart(2,'0'); return `${m}:${ss}` }
function fmtHm(iso){ try{ const d=new Date(iso); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}` }catch{return '--:--'} }
</script>




<template>
  <div class="container py-3">

    <div class="d-flex gap-2 mb-3 align-items-center">
      <button class="btn btn-outline-secondary btn-sm" @click="load">更新</button>
      <span class="text-muted">件数: {{ s.readyList.length }}</span>
    </div>

    <div class="row g-3">
      <div class="col-12 col-lg-6" v-for="t in s.readyList" :key="t.id">
        <div class="card shadow-sm">
          <div class="card-body">
            <div class="d-flex justify-content-between mb-2">
              <span class="badge bg-dark fs-5 p-2">卓 {{ t.table_no ?? '-' }}</span>
              <span class="text-muted small">経過: {{ fmtSec(t.elapsed_sec ?? 0) }}</span>
            </div>

            <div class="fw-bold fs-5 mb-3">{{ t.item_name }}</div>

            <!-- ▼ スタッフ選択（チップ） -->
            <div v-if="staffs.length" class="d-flex flex-wrap gap-2">
              <button
                v-for="st in staffs"
                :key="st.id"
                class="btn btn-outline-primary btn-sm"
                :title="staffLabel(st)"
                @click="take(t.id, st.id)"
              >
                持ってく：{{ staffLabel(st) }}
              </button>
            </div>
            <div v-else class="text-muted small mt-2">
              ※スタッフ一覧が取得できませんでした。上の「更新」を押してください。
            </div>
            <!-- ▲ スタッフ選択（チップ） -->
          </div>
        </div>
      </div>

    <!-- ▼ 今日の注文（小さな履歴） -->
    <hr class="my-4">
    <h5 class="mb-2">今日の注文（持ち出し履歴・直近50件）</h5>
    <div class="table-responsive">
      <table class="table table-sm align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th style="width:6rem;">時刻</th>
            <th style="width:6rem;">卓</th>
            <th>品名</th>
            <th style="width:10rem;">担当</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in history" :key="h.id">
            <td>{{ fmtHm(h.taken_at) }}</td>
            <td>卓 {{ h.table_no ?? '-' }}</td>
            <td class="text-truncate" style="max-width: 20rem;">{{ h.item_name }}</td>
            <td>{{ h.staff_name }}</td>
          </tr>
          <tr v-if="!history.length">
            <td colspan="4" class="text-muted text-center small">本日の履歴はまだありません</td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- ▲ 今日の注文 -->

      <div v-if="s.readyList.length===0" class="col-12">
        <div class="alert alert-light border text-center">READYなし</div>
      </div>
    </div>
  </div>
</template>
