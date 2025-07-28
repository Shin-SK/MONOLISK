<script setup>
import { onMounted, ref, computed, watch } from 'vue'
import { fetchCastSalesDetail, fetchCastItemDetails } from '@/api'
import dayjs from 'dayjs'
import { useRoute } from 'vue-router'

const { params:{ id } } = useRoute()
const dateFrom = ref(dayjs().startOf('month').format('YYYY-MM-DD'))
const dateTo   = ref(dayjs().format('YYYY-MM-DD'))
const payouts  = ref([])
const details  = ref({})

async function load(){
	const params = { from: dateFrom.value, to: dateTo.value }
	payouts.value = await fetchCastSalesDetail(id, params)
	const items   = await fetchCastItemDetails(id, params)
	details.value = {}
	items.forEach(it => {
		(details.value[it.bill_id] ??= []).push(it)
	})
}
onMounted(load)
watch([dateFrom, dateTo], load)

/* util */
const castName = computed(()=> payouts.value[0]?.cast?.stage_name || '')
const fmt      = d => new Date(d).toLocaleString()
const yen      = n => `¥${(+n||0).toLocaleString()}`
const total    = computed(()=> payouts.value.reduce((s,p)=>s+p.amount,0))


/* 指名区分を返す */
const nomType = p => {
	if (!p.bill_item) return '本指名'          // プール = 本指名
	if (p.bill_item.is_inhouse) return '場内'
	return 'フリー'
}
</script>

<template>
	<div class="container-fluid mt-4">
		<h2 class="mb-3">{{ castName }} の売上</h2>

		<!-- 期間指定 -->
		<div class="d-flex align-items-end gap-2 mb-3">
			<div>
				<label class="form-label">開始日</label>
				<input type="date" v-model="dateFrom" class="form-control" />
			</div>
			<div>
				<label class="form-label">終了日</label>
				<input type="date" v-model="dateTo" class="form-control" />
			</div>
		</div>

		<table class="table">
			<thead class="table-dark">
				<tr>
					<th>テーブル</th>
					<th>日時</th>
					<th>指名</th>
					<th class="text-end">テーブル小計</th>
					<th class="text-end">ギャラ</th>
				</tr>
			</thead>

			<tbody>
				<template v-for="p in payouts" :key="p.id">
					<!-- 親行 -->
					<tr class="align-middle"
						data-bs-toggle="collapse"
						:href="'#detail'+p.bill.id">
						<td>{{ p.bill.table_no ?? p.bill.table }}卓</td>
						<td>{{ fmt(p.bill.opened_at) }}</td>
						<td>{{ nomType(p) }}</td>
						<td class="text-end">{{ yen(p.bill.subtotal) }}</td>
						<td class="text-end fw-bold">{{ yen(p.amount) }}</td>
					</tr>

					<!-- 子行 -->
					<tr :id="'detail'+p.bill.id" class="collapse bg-light">
						<td colspan="5" class="p-0">
							<table class="table mb-0 small">
								<thead>
									<tr>
										<th>商品</th>
										<th class="text-end">個数</th>
										<th class="text-end">単価</th>
										<th class="text-end">率</th>
										<th class="text-end">バック</th>
									</tr>
								</thead>

								<tbody>
									<tr v-for="it in details[p.bill.id] ?? []" :key="it.id">
										<td>{{ it.name }}</td>
										<td class="text-end">×{{ it.qty }}</td>
										<td class="text-end">{{ yen(it.subtotal / it.qty) }}</td>
										<td class="text-end">
											{{ it.is_nomination ? '-' : (it.back_rate*100).toFixed(0)+'%' }}
										</td>
										<td class="text-end">
											{{ it.is_nomination ? '-' : yen(it.amount) }}
										</td>
									</tr>
								</tbody>

								<tfoot class="fw-bold bg-white">
									<tr>
										<td colspan="4" class="text-end">ギャラ合計</td>
										<td class="text-end">{{ yen(p.amount) }}</td>
									</tr>
								</tfoot>
							</table>
						</td>
					</tr>
				</template>
			</tbody>

			<tfoot class="fw-bold">
				<tr>
					<td colspan="4" class="text-end">総ギャラ合計</td>
					<td class="text-end">{{ yen(total) }}</td>
				</tr>
			</tfoot>
		</table>
	</div>
</template>
