<script setup>
import { ref, onMounted } from 'vue'
import { getBillMonthlyPL, getStores } from '@/api'

const monthStr = ref(new Date().toISOString().slice(0,7))
const storeId  = ref(1) 
const stores   = ref([])
const pl       = ref(null)

const yen = n => `¥${(+n||0).toLocaleString()}`

async function fetchData () {
	pl.value = await getBillMonthlyPL(monthStr.value, storeId.value)
}
onMounted(async () => {
	stores.value = await getStores()
	await fetchData()
})
</script>

<template>
	<div class="pl pl-monthly">

		<!-- ▼ pl が来てから描画する -->
		<div v-if="pl">
			<!-- ── MONTH SUMMARY ─────────────────────────── -->
			<div class="summary-area">
				<div class="box"><div class="head">売上</div><div class="number">{{ yen(pl.totals.sales_total) }}</div></div>
				<div class="box"><div class="head">来客数</div><div class="number">{{ pl.totals.guest_count }}</div></div>
				<div class="box"><div class="head">平均客単価</div><div class="number">{{ yen(pl.totals.avg_spend) }}</div></div>
				<div class="box"><div class="head">ドリンク売上</div><div class="number">{{ yen(pl.totals.drink_sales) }}</div></div>
				<div class="box"><div class="head">延長回数</div><div class="number">{{ pl.totals.extension_qty }}</div></div>
				<div class="box"><div class="head">人件費</div><div class="number">{{ yen(pl.totals.labor_cost) }}</div></div>
				<div class="box"><div class="head">営業利益</div><div class="number">{{ yen(pl.totals.operating_profit) }}</div></div>
			</div>

			<!-- ── 日次一覧 ─────────────────────────────── -->
			<table class="table table-sm table-bordered mt-3">
				<thead class="table-light">
					<tr>
						<th>日付</th><th>客数</th><th>売上</th><th>平均客単価</th>
						<th>ドリンク売上</th><th>杯数</th><th>延長</th>
						<th>人件費</th><th>営業利益</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="d in pl.days" :key="d.date">
						<td>{{ d.date }}</td>
						<td>{{ d.guest_count }}</td>
						<td>{{ yen(d.sales_total) }}</td>
						<td>{{ yen(d.avg_spend) }}</td>
						<td>{{ yen(d.drink_sales) }}</td>
						<td>{{ d.drink_qty }}</td>
						<td>{{ d.extension_qty }}</td>
						<td>{{ yen(d.labor_cost) }}</td>
						<td>{{ yen(d.operating_profit) }}</td>
					</tr>
				</tbody>
			</table>
		</div>

		<!-- ▼ ここより上は共通操作系なので常時表示で OK -->
		<div class="d-flex gap-2 mb-3">
			<input type="month" v-model="monthStr" class="form-control w-auto" />
			<select v-model="storeId" class="form-select w-auto">
				<option value="">全店舗</option>
				<option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
			</select>
			<button class="btn btn-primary" @click="fetchData">読み込み</button>
		</div>

		<div v-if="pl === null">読み込み中…</div>
	</div>
</template>

<style scoped>
.pl-monthly input,
.pl-monthly select { min-width: 130px; }
</style>
