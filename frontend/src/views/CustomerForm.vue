<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createCustomer, updateCustomer, deleteCustomer, getCustomer, getReservationsByCustomer } from '@/api'
import ReservationCard from '@/components/ReservationCard.vue'

const route		= useRoute()
const router	= useRouter()
const isEdit	= !!route.params.id

const form = ref({
	name:'', phone:'', memo:'',
	addresses:[{ label:'', address:'', is_primary:true }]
})

const histories	= ref([])

onMounted(async () => {
	if (!isEdit) return
	const data = await getCustomer(route.params.id)
	Object.assign(form.value, data)
	if (!form.value.addresses?.length)
		form.value.addresses = [{ label:'', address:'', is_primary:true }]

	histories.value = await getReservationsByCustomer(route.params.id)	// ★履歴取得
})
function ensureSinglePrimary(index) {
	form.value.addresses.forEach((a,i) => a.is_primary = i === index)
}

function addAddress() {
	form.value.addresses.push({
		label:'', address:'', is_primary:!form.value.addresses.some(a=>a.is_primary)
	})
}

async function save() {
	const fn = isEdit ? updateCustomer : createCustomer
	await fn(route.params.id, form.value)
	router.push('/customers')
}

async function remove() {
	if (!confirm('削除しますか？')) return
	await deleteCustomer(route.params.id)
	router.push('/customers')
}
</script>

<template>
<div class="customer customer-form container py-4">
	<h1 class="h4 mb-3">{{ isEdit ? '顧客編集' : '顧客登録' }}</h1>

	<div class="mb-3">
		<label class="form-label">名前</label>
		<input v-model="form.name" class="form-control">
	</div>

	<div class="mb-3">
		<label class="form-label">電話番号</label>
		<input v-model="form.phone" class="form-control">
	</div>

	<!-- 住所リスト -->
  <!-- 住所リストをテーブル表示に変更 -->
  <table class="table table-bordered table-hover align-middle table-striped">
    <thead class="table-dark">
      <tr>
        <th style="width:18%">住所名</th>
        <th>住所</th>
        <th style="width:10%" class="text-center">メイン</th>
        <th style="width:10%" class="text-center">削除</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(addr,i) in form.addresses" :key="i">
        <td>
          <input v-model="addr.label" class="form-control" placeholder="ラベル (例: 自宅)">
        </td>
        <td>
          <input v-model="addr.address" class="form-control" placeholder="住所">
        </td>
        <td class="text-center">
          <input
            type="radio"
            name="primaryAddress"
            :checked="addr.is_primary"
            @change="ensureSinglePrimary(i)"
            :title="'主住所に設定'"
          >
        </td>
        <td class="text-center">
          <button
            v-if="form.addresses.length > 1"
            class="btn btn-outline-danger btn-sm"
            @click="form.addresses.splice(i,1)"
          >
            －
          </button>
        </td>
      </tr>
    </tbody>
  </table>

  <button class="btn btn-sm btn-outline-secondary mb-3" @click="addAddress">
    ＋ 住所を追加
  </button>


	<div class="mb-3">
		<label class="form-label">メモ</label>
		<textarea v-model="form.memo" rows="3" class="form-control"></textarea>
	</div>

	<div class="d-flex justify-content-between">
		<button class="btn btn-secondary" @click="$router.back()">戻る</button>
		<div>
			<button v-if="isEdit" class="btn btn-outline-danger me-2" @click="remove">削除</button>
			<button class="btn btn-primary" @click="save">保存</button>
		</div>
	</div>


  <!-- テンプレート側：フォームの下あたりに追加 -->
  <h2 class="h4 mt-5">過去の予約履歴</h2>

  <!-- 予約が 0 件なら -->
  <p v-if="!histories.length" class="text-muted">まだ予約はありません</p>

  <!-- 1 件以上あるとき：カードで表示 -->
  <div v-else class="history-list">
    <!-- “Reservations” で使っているカードコンポーネントが
      ReservationCard.vue だと仮定 -->
    <ReservationCard
      v-for="r in histories"
      :key="r.id"
      :reservation="r"
      class="mb-3"
    />
  </div>
</div>
</template>
