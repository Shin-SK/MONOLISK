<!-- BillPLDaily.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { getBillDailyPL, getStores } from '@/api'

const dateStr = ref(new Date().toISOString().slice(0, 10))
const storeId = ref(null)               // ← 初期値 null に変更
const stores  = ref([])
const pl      = ref(null)

const yen = n => `¥${(+n || 0).toLocaleString()}`

async function fetchData () {
  // storeId が必須。まだ取得前なら何もしない
  if (!storeId.value) return
  pl.value = await getBillDailyPL(dateStr.value, storeId.value)
}

async function loadStores () {
  stores.value = await getStores()
  // ❶ 最初の店舗 ID を必ずセット
  storeId.value = stores.value[0]?.id || null
}

onMounted(async () => {
  await loadStores()
  await fetchData()                    // ❷ storeId セット後に呼ぶ
})
</script>

<template>
  <div class="pl pl-daily p-4 container">
    <template v-if="pl">
      <!-- <h3 class="mb-3">
				日次 P/L ({{ pl.date }})
			</h3> -->
      <div class="d-flex align-items-center gap-2 mb-3">
        <input
          v-model="dateStr"
          type="date"
          class="form-control w-auto"
        >
        <button
          class="btn btn-primary"
          @click="fetchData"
        >
          読み込み
        </button>
      </div>

      <div class="summary-area">
        <div class="box">
          <div class="head">
            売上合計
          </div><div class="number">
            {{ yen(pl.sales_total) }}
          </div>
        </div>
        <div class="box">
          <div class="head">
            人件費
          </div><div class="number">
            {{ yen(pl.labor_cost) }}
          </div>
        </div>
        <div class="box">
          <div class="head">
            営業利益
          </div><div class="number">
            {{ yen(pl.operating_profit) }}
          </div>
        </div>
      </div>

      <table class="table table-bordered table-striped">
        <tbody>
          <tr>
            <th class="w-25">
              来客数
            </th><td class="text-end">
              {{ pl.guest_count }}
            </td>
          </tr>
          <tr>
            <th>平均客単価</th><td class="text-end">
              {{ yen(pl.avg_spend) }}
            </td>
          </tr>
          <tr>
            <th>ドリンク売上</th><td class="text-end">
              {{ yen(pl.drink_sales) }}
            </td>
          </tr>
          <tr>
            <th>ドリンク杯数</th><td class="text-end">
              {{ pl.drink_qty }}
            </td>
          </tr>
          <tr>
            <th>ドリンク単価</th><td class="text-end">
              {{ yen(pl.drink_unit_price) }}
            </td>
          </tr>
          <tr>
            <th>延長回数</th><td class="text-end">
              {{ pl.extension_qty }}
            </td>
          </tr>
          <tr>
            <th>VIP比率</th><td class="text-end">
              {{ (pl.vip_ratio * 100).toFixed(1) }}%
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <div
      v-else
      class="text-muted"
    >
      読み込み中…
    </div>
  </div>
</template>

<style scoped>
.pl-daily input,
.pl-daily select { min-width: 130px; }
</style>
