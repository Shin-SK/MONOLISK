<script setup>
import { ref, onMounted } from 'vue'
import { searchCustomers, createCustomer } from '@/api'

const keyword	= ref('')
const results	= ref([])
const loading	= ref(false)

async function fetch() {
	loading.value = true
	results.value = await searchCustomers(keyword.value)
	loading.value = false
}
onMounted(fetch)

/* ---------- 新規登録（簡易 prompt 版） ---------- */
async function addCustomer() {
	const name	= prompt('顧客名');		if (!name)	return
	const phone	= prompt('電話番号');		if (!phone)	return
	const addr	= prompt('住所')	|| ''
	const memo	= prompt('メモ')	|| ''

	await createCustomer({
		name,
		phone,
		memo,
		addresses:[{ label:'', address:addr, is_primary:true }]
	})
	alert('登録しました')
	await fetch()
}

/* ---------- 主住所ヘルパ ---------- */
function primaryAddress(c) {
	const primary = c.addresses?.find(a => a.is_primary)
	return primary ? primary.address : c.addresses?.[0]?.address || ''
}
</script>

<template>
<div class="customer customer-list container-fluid py-4">
	<h1 class="h4 mb-3">顧客検索 / 登録</h1>

	<!-- 検索バー -->
	<div class="input-group mb-3">
		<input v-model="keyword" @keyup.enter="fetch"
			   class="form-control" placeholder="名前 または 電話番号">
		<button class="btn btn-outline-secondary" @click="fetch">検索</button>
		<button class="btn btn-primary" @click="addCustomer">＋ 登録</button>
	</div>

	<!-- 一覧 -->
	<table class="table table-bordered table-hover align-middle table-striped" v-if="results.length">
		<thead>
			<tr>
				<th>ID</th><th>名前</th><th>電話</th><th>住所</th><th>メモ</th><th class="text-end">編集</th>
			</tr>
		</thead>
		<tbody>
			<tr v-for="c in results" :key="c.id">
				<td>{{ c.id }}</td>
				<td>{{ c.name }}</td>
				<td>{{ c.phone }}</td>
				<td>{{ primaryAddress(c) }}</td>
				<td class="pre-line">{{ c.memo }}</td>
				<td class="text-end">
					<RouterLink :to="`/customers/${c.id}`" class="btn btn-sm btn-outline-secondary">
						編集
					</RouterLink>
				</td>
			</tr>
		</tbody>
	</table>

	<p v-else class="text-muted" v-if="!loading">結果がありません</p>
	<p v-if="loading">読み込み中...</p>
</div>
</template>
