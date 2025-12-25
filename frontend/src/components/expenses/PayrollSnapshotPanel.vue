<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  snapshot: { type: Object, default: null },
  dirty: { type: Boolean, default: false },
  billId: { type: [Number, String], default: null },
  castId: { type: [Number, String], default: null },
})

const open = ref(false)

const fmtYen = v => `¥${Number(v || 0).toLocaleString('ja-JP')}`
const fmtNum = v => Number(v || 0).toLocaleString('ja-JP')

const summaryTotals = computed(() => {
  const t = props.snapshot?.totals || {}
  return [
    { key: 'labor_total', label: '人件費合計', value: t.labor_total ?? t.total ?? t.grand_total },
    { key: 'nomination_total', label: '本指名/同伴', value: t.nomination_total },
    { key: 'item_total', label: 'バック(品目)', value: t.item_total },
    { key: 'hourly_total', label: '時給', value: t.hourly_total },
  ].filter(x => x.value !== undefined && x.value !== null)
})

const byCast = computed(() => {
  const list = props.snapshot?.by_cast || []
  if (!props.castId) return list
  return list.filter(c => String(c.cast_id) === String(props.castId))
})

const items = computed(() => props.snapshot?.items || [])

const headerId = computed(() => `payroll-snap-${props.billId || 'bill'}`)
</script>

<template>
  <div class="card border-0 shadow-sm">
    <div class="card-header bg-light d-flex align-items-center justify-content-between">
      <div class="d-flex align-items-center gap-2">
        <span class="fw-semibold">給与計算（参考）</span>
        <span class="text-muted small">伝票確定時点のスナップショット。編集不可。</span>
        <span v-if="dirty" class="badge bg-danger">変更あり</span>
      </div>
      <button class="btn btn-sm btn-outline-secondary" type="button" @click="open = !open" :aria-expanded="open" :aria-controls="headerId">
        {{ open ? '閉じる' : '開く' }}
      </button>
    </div>

    <div class="card-body">
      <div class="d-flex flex-wrap gap-3 align-items-center">
        <div class="d-flex align-items-baseline gap-2">
          <span class="text-muted">人件費合計</span>
          <strong class="fs-5">{{ fmtYen(summaryTotals[0]?.value || 0) }}</strong>
        </div>
        <div class="d-flex flex-wrap gap-3 text-muted small">
          <div v-for="s in summaryTotals.slice(1)" :key="s.key" class="d-flex gap-1 align-items-center">
            <span>{{ s.label }}:</span>
            <span class="fw-semibold">{{ fmtYen(s.value) }}</span>
          </div>
        </div>
      </div>

      <div v-if="!open" class="text-muted small mt-2">詳細を開くと内訳とJSONが確認できます。</div>

      <div v-if="open" class="mt-3" :id="headerId">
        <div class="mb-3">
          <div class="fw-semibold mb-1">キャスト別内訳</div>
          <div v-if="!byCast.length" class="text-muted small">データなし</div>
          <div v-for="c in byCast" :key="c.cast_id" class="border rounded p-2 mb-2">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <span class="fw-semibold">Cast #{{ c.cast_id }}</span>
                <span v-if="c.stay_type" class="badge bg-secondary ms-2">{{ c.stay_type }}</span>
              </div>
              <div class="fw-semibold">{{ fmtYen(c.amount) }}</div>
            </div>
            <ul class="mb-0 mt-2 small text-muted">
              <li v-for="(b, idx) in c.breakdown || []" :key="idx">
                <span class="fw-semibold">{{ b.label || b.type || '明細' }}:</span>
                <span>{{ fmtYen(b.amount) }}</span>
                <span v-if="b.basis" class="ms-1">(basis: {{ JSON.stringify(b.basis) }})</span>
              </li>
              <li v-if="!(c.breakdown && c.breakdown.length)" class="text-muted">内訳データなし</li>
            </ul>
          </div>
        </div>

        <div class="mb-3">
          <div class="fw-semibold mb-1">アイテム別配分</div>
          <div class="table-responsive">
            <table class="table table-sm align-middle">
              <thead>
                <tr><th>ID</th><th>品目</th><th class="text-end">数量</th><th class="text-end">単価</th><th class="text-end">小計</th><th>給与効果</th></tr>
              </thead>
              <tbody>
                <tr v-for="it in items" :key="it.bill_item_id || it.id">
                  <td>#{{ it.bill_item_id || it.id }}</td>
                  <td>{{ it.name || '(不明)' }}</td>
                  <td class="text-end">{{ fmtNum(it.qty) }}</td>
                  <td class="text-end">{{ fmtYen(it.unit_price) }}</td>
                  <td class="text-end">{{ fmtYen(it.subtotal) }}</td>
                  <td>
                    <div v-if="it.payroll_effects?.length" class="small">
                      <div v-for="(p, idx) in it.payroll_effects" :key="idx" class="d-flex justify-content-between">
                        <span>Cast #{{ p.cast_id }} ({{ p.type || 'effect' }})</span>
                        <span class="fw-semibold">{{ fmtYen(p.amount) }}</span>
                      </div>
                    </div>
                    <span v-else class="text-muted small">なし</span>
                  </td>
                </tr>
                <tr v-if="!items.length"><td colspan="6" class="text-muted small">データなし</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="mb-3">
          <div class="fw-semibold mb-1">Raw JSON</div>
          <pre class="bg-light border rounded p-2 small overflow-auto" style="max-height: 240px;">{{ JSON.stringify(snapshot, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>
