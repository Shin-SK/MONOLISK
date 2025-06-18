<!-- src/views/ReservationFormDriver.vue -->
<script setup>
import { ref, onMounted, watch } from 'vue'           // ← watch を追加
import { useRoute, useRouter } from 'vue-router'
import { getReservation, updateReservation } from '@/api'
import { useUser } from '@/stores/useUser'

const userStore = useUser()
const router    = useRouter()
const route     = useRoute()

const rsv       = ref(null)
const received  = ref(null)

/* ▼ 追加： mini-nav の状態と画面遷移 */
const mode = ref('timeline')		// 'timeline' | 'list'

watch(mode, v => {
	if (v === 'timeline') router.push('/driver')             // タイムライン画面
	else if (v === 'list') router.push('/driver?view=list')  // リスト画面
})

/* 予約取得 */
async function reload () {
	rsv.value      = await getReservation(route.params.id)
	received.value = rsv.value.received_amount
}
onMounted(reload)

/* 保存 */
async function save () {
	await updateReservation(rsv.value.id, { received_amount: received.value })
	await reload()
	alert('受取金額を更新しました')
	router.push('/driver')
}
</script>




<template>

	<header class="header">
		<div class="header__wrap container">
			<div class="area">
				<div class="icon">
					<img :src="userStore.avatar" class="rounded-circle"/>
				</div>
			</div>

			<!-- ボタン押したら、タイムラインかカレンダーに飛びたい -->
			<div class="mini-nav">
				<button
					class="button"
					:class="mode==='list' ? 'btn btn-primary active' : 'btn btn-outline-primary'"
					@click="mode='list'">
					<span class="material-symbols-outlined">list</span>
				</button>

				<button
					class="button"
					:class="mode==='timeline' ? 'btn btn-primary active' : 'btn btn-outline-primary'"
					@click="mode='timeline'">
					<span class="material-symbols-outlined">view_timeline</span>
				</button>
			</div>
		</div>
	</header>

<div class="container py-4" v-if="rsv">
  <h1 class="h4 mb-4">予約 #{{ rsv.id }}（ドライバー）</h1>

<table class="table">
	<tbody>
		<tr><th>キャスト</th><td>{{ rsv.cast_names.join(', ') }}</td></tr>
		<tr><th>開始</th><td>{{ new Date(rsv.start_at).toLocaleString() }}</td></tr>

		<!-- ▼ 追加した 3 行 -->
		<tr v-if="rsv.course_minutes">
			<th>コース</th>
			<td>{{ rsv.course_minutes }} 分</td>
		</tr>

		<tr v-if="rsv.customer_address">
			<th>住所</th>
			<td>{{ rsv.customer_address }}</td>
		</tr>

		<tr v-if="rsv.charges.length">
			<th>オプション</th>
			<td>
				<span
					v-for="ch in rsv.charges"
					:key="ch.id"
					class="badge bg-secondary me-1"
				>
					{{ ch.option_name }} {{ ch.amount }}円
				</span>
			</td>
		</tr>
		<!-- ▲ ここまで -->

		<tr><th>お客様名</th><td>{{ rsv.customer_name }}</td></tr>
		<tr><th>見積</th><td>{{ rsv.expected_amount.toLocaleString() }} 円</td></tr>
	</tbody>
</table>


  <div class="mb-3">
    <label class="form-label">受取金額</label>
    <input type="number" class="form-control" v-model.number="received" />
  </div>

  <button class="btn btn-primary" @click="save">保存</button>
</div>
</template>
