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
	<div class="pl-daily p-4">
		<h3 class="mb-3">日次 P/L</h3>

		<div class="d-flex align-items-center gap-2 mb-3">
			<input type="date" v-model="dateStr" class="form-control w-auto" />
			<select v-model="storeId" class="form-select w-auto">
				<option value="">全店舗</option>
				<option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
			</select>
			<button class="btn btn-primary" @click="fetchData">読み込み</button>
		</div>

		<table v-if="pl" class="table table-bordered table-striped">
			<tbody>
				<tr><th class="w-50">日付</th><td>{{ pl.date }}</td></tr>
				<tr><th>店舗</th><td>{{ pl.store_id || '全店舗' }}</td></tr>
				<tr><th>来客数</th><td>{{ pl.guest_count }}</td></tr>
				<tr><th>売上合計</th><td>{{ yen(pl.sales_total) }}</td></tr>
				<tr><th>平均客単価</th><td>{{ yen(pl.avg_spend) }}</td></tr>
				<tr><th>ドリンク売上</th><td>{{ yen(pl.drink_sales) }}</td></tr>
				<tr><th>ドリンク杯数</th><td>{{ pl.drink_qty }}</td></tr>
				<tr><th>ドリンク単価</th><td>{{ yen(pl.drink_unit_price) }}</td></tr>
				<tr><th>延長回数</th><td>{{ pl.extension_qty }}</td></tr>
				<tr><th>VIP比率</th><td>{{ (pl.vip_ratio * 100).toFixed(1) }}%</td></tr>
				<tr><th>人件費</th><td>{{ yen(pl.labor_cost) }}</td></tr>					<!-- ★ -->
				<tr><th>営業利益</th><td>{{ yen(pl.operating_profit) }}</td></tr>			<!-- ★ -->
			</tbody>
		</table>

		<div v-else class="text-muted">読み込み中…</div>
	</div>
</template>

<style scoped>
.pl-daily input,
.pl-daily select { min-width: 130px; }
</style>
