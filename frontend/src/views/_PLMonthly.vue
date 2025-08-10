<script setup>
import { ref, watch, onMounted } from 'vue'
import { getBillMonthlyPL }      from '@/api'

/* ─── フィルタ入力（月） ───────────────────── */
const yearMonth = ref(new Date().toISOString().slice(0, 7))

/* ─── 画面ステート ───────────────────────── */
const rows  = ref([])

/* ★ 初期値は “完成形と同じキー構成” でゼロ埋め  */
const total = ref({
  sales_total   : 0,
  cast_labor    : 0,
  driver_labor  : 0,
  custom_expense: 0,
  gross_profit  : 0,
  sales_cash    : 0,
  sales_card    : 0,
})

/* ─── データ取得 ────────────────────────── */
async function fetchData () {
  try {
    console.log('[monthlyPL] call', yearMonth.value)

    const data = await getBillMonthlyPL(yearMonth.value)

    console.log('[monthlyPL] response', data)

    rows.value  = data?.days ?? []
    total.value = { ...total.value, ...(data?.monthly_total ?? {}) }
  } catch (err) {
    console.error('[monthlyPL] fetch error', err)
  }
}

onMounted(fetchData)
watch(yearMonth, fetchData)
</script>

<template>
  <div class="pl pl-monthly container-fluid py-4">
    <!-- ── サマリー ───────────────────────── -->
    <div class="summary-area">
      <div class="box">
        <div class="head">
          粗利益
        </div>
        <div class="number">
          {{ $yen(total?.gross_profit ?? 0) }}
        </div>
      </div>

      <div class="box">
        <div class="head">
          売上
        </div>
        <div class="number">
          {{ $yen(total?.sales_total ?? 0) }}
        </div>
      </div>

      <div class="box">
        <div class="head">
          キャスト人件費
        </div>
        <div class="number">
          {{ $yen(total?.cast_labor ?? 0) }}
        </div>
      </div>

      <div class="box">
        <div class="head">
          ドライバー人件費
        </div>
        <div class="number">
          {{ $yen(total?.driver_labor ?? 0) }}
        </div>
      </div>

      <div class="box">
        <div class="head">
          カスタム経費
        </div>
        <div class="number">
          {{ $yen(total?.custom_expense ?? 0) }}
        </div>
      </div>
    </div>

    <!-- ── フィルタ ───────────────────────── -->
    <div class="d-flex gap-3 mb-3 align-items-end">
      <div>
        <label class="form-label small mb-1">対象月</label>
        <input
          v-model="yearMonth"
          type="month"
          class="form-control"
          style="max-width:180px"
        >
      </div>
    </div>

    <!-- ── 明細テーブル ─────────────────────── -->
    <div class="table-responsive">
      <table class="table table-sm align-middle table-striped">
        <thead class="table-dark">
          <tr>
            <th class="text-nowrap">
              日付
            </th>
            <th class="text-end">
              現金
            </th>
            <th class="text-end">
              カード
            </th>
            <th class="text-end">
              売上
            </th>
            <th class="text-end">
              キャスト人件費
            </th>
            <th class="text-end">
              ドライバー人件費
            </th>
            <th class="text-end">
              カスタム経費
            </th>
            <th class="text-end">
              粗利益
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="d in rows"
            :key="d.date"
          >
            <td class="text-nowrap">
              {{ d.date }}
            </td>
            <td class="text-end">
              {{ $yen(d?.sales_cash ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(d?.sales_card ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(d?.sales_total ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(d?.cast_labor ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(d?.driver_labor ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(d?.custom_expense ?? 0) }}
            </td>
            <td
              class="text-end fw-semibold"
              :class="(d?.gross_profit ?? 0) < 0 ? 'text-danger' : ''"
            >
              {{ $yen(d?.gross_profit ?? 0) }}
            </td>
          </tr>
        </tbody>

        <tfoot>
          <tr class="table-secondary fw-bold">
            <td class="text-end">
              合計
            </td>
            <td class="text-end">
              {{ $yen(total?.sales_total ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(total?.cast_labor ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(total?.driver_labor ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(total?.custom_expense ?? 0) }}
            </td>
            <td class="text-end">
              {{ $yen(total?.gross_profit ?? 0) }}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>
