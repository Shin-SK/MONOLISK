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
const form = ref({
  received_amount : 0,   // 受取
  pay_card        : 0,
  pay_cash        : 0,
  revenues        : [{ label:'', amount:0 }],
  expenses        : [{ label:'', amount:0 }],
})

/* ▼ 追加： mini-nav の状態と画面遷移 */
const mode = ref('timeline')		// 'timeline' | 'list'

watch(mode, v => {
	if (v === 'timeline') router.push('/driver')             // タイムライン画面
	else if (v === 'list') router.push('/driver?view=list')  // リスト画面
})

/* 予約取得 */
async function reload () {
	rsv.value      = await getReservation(route.params.id)
	form.value.received_amount = rsv.value.received_amount
	form.value.pay_card = rsv.value.payments.find(p => p.method === 'card')?.amount || 0
	form.value.pay_cash = res.payments.find(p => p.method==='cash')?.amount || 0
	form.value.revenues = res.manual_entries
	    .filter(e => e.entry_type==='revenue')
	    .map(e => ({ label:e.label, amount:e.amount })) || [{label:'',amount:0}]
	form.value.expenses = res.manual_entries
	    .filter(e => e.entry_type==='expense')
	    .map(e => ({ label:e.label, amount:e.amount })) || [{label:'',amount:0}]
}
onMounted(reload)

/* 保存 */
async function save () {
	  const payments = [
	    ...(form.value.pay_card ? [{ method:'card', amount:Number(form.value.pay_card) }] : []),
	    ...(form.value.pay_cash ? [{ method:'cash', amount:Number(form.value.pay_cash) }] : []),
	  ]
	  const manual_entries = [
	    ...form.value.revenues
	        .filter(e => e.label && e.amount)
	        .map(e => ({ entry_type:'revenue', label:e.label, amount:Number(e.amount) })),
	    ...form.value.expenses
	        .filter(e => e.label && e.amount)
	        .map(e => ({ entry_type:'expense', label:e.label, amount:Number(e.amount) })),
	  ]
	
	  await updateReservation(rsv.value.id, {
	    received_amount : form.value.received_amount,
	    payments,
	    manual_entries,
	  })
	await reload()
	alert('受取金額を更新しました')
	router.push('/driver')
}
</script>




<template>
  <div
    v-if="rsv"
    class="container py-4"
  >
    <h1 class="h4 mb-4">
      予約 #{{ rsv.id }}（ドライバー）
    </h1>

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

    <!-- ◆ 支払い方法 ◆ -->
    <div class="area">
      <div class="h5">
        支払い
      </div>
      <div class="row g-3">
        <div class="col-md-3">
          <label class="form-label">カード</label>
          <input
            v-model.number="form.pay_card"
            type="number"
            class="form-control"
            min="0"
          >
        </div>
        <div class="col-md-3">
          <label class="form-label">現金</label>
          <input
            v-model.number="form.pay_cash"
            type="number"
            class="form-control"
            min="0"
          >
        </div>
      </div>
    </div>


    <!-- ◆ マニュアル売上 ◆ -->
    <div class="area">
      <div class="h5">
        マニュアル売上
      </div>
      <div
        v-for="(row,i) in form.revenues"
        :key="i"
        class="row g-2 mb-2"
      >
        <div class="col">
          <input
            v-model="row.label"
            placeholder="ラベル"
            class="form-control"
          >
        </div>
        <div class="col">
          <input
            v-model.number="row.amount"
            type="number"
            min="0"
            placeholder="金額"
            class="form-control"
          >
        </div>
        <div class="col-auto">
          <button
            v-if="form.revenues.length>1"
            class="btn btn-outline-danger"
            @click="form.revenues.splice(i,1)"
          >
            －
          </button>
        </div>
      </div>
      <button
        class="btn btn-sm btn-outline-primary"
        @click="form.revenues.push({label:'',amount:0})"
      >
        ＋ 行を追加
      </button>
    </div>

    <!-- ◆ マニュアル経費 ◆ -->
    <div class="area">
      <div class="h5">
        マニュアル経費
      </div>
      <div
        v-for="(row,i) in form.expenses"
        :key="i"
        class="row g-2 mb-2"
      >
        <div class="col">
          <input
            v-model="row.label"
            placeholder="ラベル"
            class="form-control"
          >
        </div>
        <div class="col">
          <input
            v-model.number="row.amount"
            type="number"
            min="0"
            placeholder="金額"
            class="form-control"
          >
        </div>
        <div class="col-auto">
          <button
            v-if="form.expenses.length>1"
            class="btn btn-outline-danger"
            @click="form.expenses.splice(i,1)"
          >
            －
          </button>
        </div>
      </div>
      <button
        class="btn btn-sm btn-outline-primary"
        @click="form.expenses.push({label:'',amount:0})"
      >
        ＋ 行を追加
      </button>
    </div>


    <div class="mb-3">
      <label class="form-label">受取金額</label>
      <input
        v-model.number="received"
        type="number"
        class="form-control"
      >
    </div>

    <button
      class="btn btn-primary"
      @click="save"
    >
      保存
    </button>
  </div>
</template>
