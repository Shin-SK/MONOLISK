<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { fetchBill } from '@/api'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)

const bill = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const yen  = n => `¥${(Number(n||0)).toLocaleString()}`
const dt   = s => s ? dayjs(s).format('YYYY/MM/DD HH:mm') : '—'

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    bill.value = await fetchBill(id)
  } catch (e) {
    console.error(e); errorMsg.value = '伝票が見つかりません'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container-fluid py-3">
    <div class="d-flex align-items-center justify-content-between mb-2">
      <h1 class="h5 mb-0">伝票 #{{ id }}</h1>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-secondary btn-sm" @click="router.back()">戻る</button>
      </div>
    </div>

    <div v-if="errorMsg" class="alert alert-danger">{{ errorMsg }}</div>
    <div v-if="loading">Loading…</div>

    <div v-if="bill" class="card">
      <div class="card-body">
        <div class="row g-3">
          <div class="col-md-3"><small class="text-muted">卓</small><div class="fw-bold">{{ bill.table?.name || '—' }}</div></div>
          <div class="col-md-3"><small class="text-muted">クローズ</small><div class="fw-bold">{{ dt(bill.closed_at) }}</div></div>
          <div class="col-md-3"><small class="text-muted">支払(現金)</small><div class="fw-bold">{{ yen(bill.paid_cash) }}</div></div>
          <div class="col-md-3"><small class="text-muted">支払(カード)</small><div class="fw-bold">{{ yen(bill.paid_card) }}</div></div>
        </div>

        <hr>

        <h6 class="mb-2">明細</h6>
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr><th>ID</th><th>品目</th><th class="text-end">単価</th><th class="text-end">数量</th><th class="text-end">小計</th></tr>
            </thead>
            <tbody>
              <tr v-for="it in bill.items || []" :key="it.id">
                <td>#{{ it.id }}</td>
                <td>{{ it.item_master?.name || it.name }}</td>
                <td class="text-end">{{ yen(it.price) }}</td>
                <td class="text-end">{{ it.qty }}</td>
                <td class="text-end">{{ yen((it.price||0) * (it.qty||0)) }}</td>
              </tr>
              <tr v-if="!bill.items?.length"><td colspan="5" class="text-muted">明細なし</td></tr>
            </tbody>
            <tfoot>
              <tr><th colspan="4" class="text-end">小計</th><th class="text-end">{{ yen(bill.subtotal) }}</th></tr>
              <tr><th colspan="4" class="text-end">サービス</th><th class="text-end">{{ yen(bill.service_amount) }}</th></tr>
              <tr><th colspan="4" class="text-end">税</th><th class="text-end">{{ yen(bill.tax_amount) }}</th></tr>
              <tr><th colspan="4" class="text-end">合計</th><th class="text-end fw-bold">{{ yen(bill.grand_total ?? bill.total) }}</th></tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
