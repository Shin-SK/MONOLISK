<script setup>
import { ref, watch, onMounted } from 'vue'
import dayjs from 'dayjs'
import { fetchBillsList, downloadBillExcel, downloadDailyZip, downloadDailyReport } from '@/api'

const selectedDate = ref(dayjs().format('YYYY-MM-DD'))
const bills = ref([])
const loading = ref(false)
const downloading = ref({})
const downloadingZip = ref(false)
const downloadingReport = ref(false)

const yen = n => `¥${(Number(n || 0)).toLocaleString()}`
const formatTime = s => s ? dayjs(s).format('HH:mm') : '-'

function castNames(bill) {
  const names = (bill.stays || [])
    .map(s => s.cast?.stage_name || s.cast?.name)
    .filter(Boolean)
  return [...new Set(names)].join(', ') || '-'
}

async function loadBills() {
  loading.value = true
  try {
    const all = await fetchBillsList({
      params: { closed_at__date: selectedDate.value },
      noCache: true,
    })
    // クライアント側でもフィルタ（APIが closed_at__date 未対応の場合のフォールバック）
    bills.value = all.filter(b => {
      if (!b.closed_at) return false
      return dayjs(b.closed_at).format('YYYY-MM-DD') === selectedDate.value
    })
  } catch (e) {
    console.error(e)
    bills.value = []
  } finally {
    loading.value = false
  }
}

async function dlExcel(bill) {
  downloading.value[bill.id] = true
  try {
    const blob = await downloadBillExcel(bill.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bill_${bill.id}_${selectedDate.value}.xlsx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    alert('Excelダウンロードに失敗しました')
  } finally {
    downloading.value[bill.id] = false
  }
}

async function dlZip() {
  downloadingZip.value = true
  try {
    const blob = await downloadDailyZip(selectedDate.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedDate.value}_bills.zip`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    if (e.response && e.response.status === 404) {
      alert('この日の伝票はありません')
    } else {
      console.error(e)
      alert('ZIPダウンロードに失敗しました')
    }
  } finally {
    downloadingZip.value = false
  }
}

async function dlReport() {
  downloadingReport.value = true
  try {
    const blob = await downloadDailyReport(selectedDate.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedDate.value}_daily_report.xlsx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    if (e.response && e.response.status === 404) {
      alert('この日の伝票はありません')
    } else {
      console.error(e)
      alert('日報ダウンロードに失敗しました')
    }
  } finally {
    downloadingReport.value = false
  }
}

watch(selectedDate, () => loadBills())
onMounted(() => loadBills())
</script>

<template>
  <div class="container-fluid py-3">

    <!-- 日付選択 -->
    <div class="d-flex align-items-center gap-2 mb-3">
      <label class="form-label mb-0 fw-bold">営業日:</label>
      <input type="date" class="form-control bg-white" style="max-width:200px" v-model="selectedDate" />
    </div>

    <!-- 上部ボタン -->
    <div class="d-flex gap-2 mb-3 flex-md-row flex-column">
      <button
        class="btn btn-outline-primary btn-sm bg-white"
        :disabled="downloadingZip || bills.length === 0"
        @click="dlZip">
        <span v-if="downloadingZip" class="spinner-border spinner-border-sm me-1"></span>
        この日の伝票をまとめてダウンロード
      </button>
      <button
        class="btn btn-outline-primary btn-sm bg-white"
        :disabled="downloadingReport || bills.length === 0"
        @click="dlReport">
        <span v-if="downloadingReport" class="spinner-border spinner-border-sm me-1"></span>
        この日の売上日報をダウンロード
      </button>
    </div>

    <!-- ローディング -->
    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm"></div>
      <span class="ms-2">読み込み中...</span>
    </div>

    <!-- 伝票一覧 -->
    <div v-else-if="bills.length === 0" class="text-muted py-4 text-center">
      この日の伝票はありません
    </div>

    <div v-else class="table-responsive">
      <table class="table table-hover align-middle text-nowrap">
        <thead class="table-light">
          <tr>
            <th>#</th>
            <th>テーブル</th>
            <th>人数</th>
            <th>開始</th>
            <th>終了</th>
            <th>キャスト</th>
            <th class="text-end">総額</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="bill in bills" :key="bill.id">
            <td>{{ bill.id }}</td>
            <td>
              <template v-if="bill.tables && bill.tables.length">
                {{ bill.tables.map(t => t.code || t.id).join(', ') }}
              </template>
              <template v-else-if="bill.table">
                {{ bill.table.code || bill.table.id }}
              </template>
              <template v-else>-</template>
            </td>
            <td>{{ bill.pax }}</td>
            <td>{{ formatTime(bill.opened_at) }}</td>
            <td>{{ formatTime(bill.closed_at) }}</td>
            <td>{{ castNames(bill) }}</td>
            <td class="text-end">{{ yen(bill.grand_total) }}</td>
            <td>
              <button
                class="btn btn-sm btn-outline-success text-nowrap"
                :disabled="downloading[bill.id]"
                @click="dlExcel(bill)">
                <template v-if="downloading[bill.id]">
                  <span class="spinner-border spinner-border-sm"></span>
                </template>
                <template v-else>Excel</template>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
