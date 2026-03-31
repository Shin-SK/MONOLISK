<!-- src/views/CastManualSubtotal.vue  キャスト売上（手入力） -->
<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import { fetchCasts, fetchCastManualSubtotals, saveCastManualSubtotals } from '@/api'

const targetDate = ref(dayjs().format('YYYY-MM-DD'))
const casts      = ref([])
const rows       = ref([])   // { cast_id, manual_subtotal, memo }
const saving     = ref(false)
const message    = ref('')

async function load () {
  message.value = ''
  const [castList, saved] = await Promise.all([
    fetchCasts(),
    fetchCastManualSubtotals(targetDate.value),
  ])
  const list = Array.isArray(castList?.results) ? castList.results : (Array.isArray(castList) ? castList : [])
  casts.value = list

  // 保存済みデータをマップ化
  const savedMap = new Map()
  for (const s of (saved || [])) {
    savedMap.set(s.cast, s)
  }

  // キャスト一覧 → 行を作る（保存済みがあればその値、なければ空）
  rows.value = list.map(c => {
    const existing = savedMap.get(c.id)
    return {
      cast_id: c.id,
      stage_name: c.stage_name,
      manual_subtotal: existing ? existing.manual_subtotal : '',
      memo: existing ? existing.memo : '',
    }
  })
}

async function save () {
  saving.value = true
  message.value = ''
  try {
    // 値が入っている行のみ送信
    const payload = rows.value
      .filter(r => r.manual_subtotal !== '' && r.manual_subtotal !== null)
      .map(r => ({
        cast: r.cast_id,
        work_date: targetDate.value,
        manual_subtotal: Number(r.manual_subtotal) || 0,
        memo: r.memo || '',
      }))
    if (!payload.length) {
      message.value = '保存する行がありません'
      return
    }
    await saveCastManualSubtotals(payload)
    message.value = '保存しました'
  } catch (e) {
    message.value = '保存に失敗しました'
    console.error(e)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container-fluid mt-4">
    <h5 class="mb-3">キャスト売上（手入力）</h5>

    <!-- 日付選択 -->
    <div class="d-flex gap-2 mb-3 align-items-center">
      <input v-model="targetDate" type="date" class="form-control form-control-sm" style="max-width:180px" />
      <button class="btn btn-secondary btn-sm" @click="load" style="white-space:nowrap">表示</button>
    </div>

    <!-- メッセージ -->
    <div v-if="message" class="alert alert-info py-1 px-2 small">{{ message }}</div>

    <!-- 一覧 -->
    <div class="table-responsive">
      <table class="table table-striped">
        <thead class="table-dark">
          <tr>
            <th>キャスト</th>
            <th style="width:180px">売上（円）</th>
            <th>メモ</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.cast_id">
            <td class="align-middle">{{ r.stage_name }}</td>
            <td>
              <input
                v-model.number="r.manual_subtotal"
                type="number"
                class="form-control form-control-sm"
                placeholder="未入力"
                min="0"
              />
            </td>
            <td>
              <input
                v-model="r.memo"
                type="text"
                class="form-control form-control-sm"
                placeholder=""
              />
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="3" class="text-center text-muted">キャストが登録されていません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 保存 -->
    <button class="btn btn-primary" :disabled="saving" @click="save">
      {{ saving ? '保存中…' : '保存' }}
    </button>
  </div>
</template>

<style scoped>
input { background-color: white; }
table td, table th { white-space: nowrap; }
</style>
