<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import dayjs from 'dayjs'
import {
  getExpenseCategories,
  getExpenseEntries,
  createExpenseEntry,
  updateExpenseEntry,
  deleteExpenseEntry,
} from '@/api'

/* props */
const props = defineProps({
  storeId     : { type:[Number,String], default:null },
  defaultDate : { type:String, default: dayjs().format('YYYY-MM-DD') },
})

/* 定数 */
const CUSTOM_CAT_ID = 6    // カスタム経費

/* ---------- state ---------- */
const date        = ref(props.defaultDate)
const categories  = ref([])                // 全カテゴリ
const fixedCats   = ref([])                // is_fixed == true
const fixedVals   = reactive({})           // {catId: amount}
const fixedIds    = reactive({})           // {catId: entryId|null}
const customs     = ref([])                // カスタム行 [{id|null,label,amount,date}]
                                            // category は常に CUSTOM_CAT_ID

/* ---------- 行操作 ---------- */
function addRow () {
  customs.value.push({ id:null, label:'', amount:0, date:date.value })
}
function removeRow (i, row) {
  if (row.id) deleteExpenseEntry(row.id)
  customs.value.splice(i,1)
}

/* ---------- 取得 ---------- */
async function load () {
  const [cats, rows] = await Promise.all([
    getExpenseCategories(),
    getExpenseEntries({ date: date.value, store: props.storeId })
  ])
  categories.value = cats
  fixedCats.value  = cats.filter(c => c.is_fixed)

  // 初期化
  fixedCats.value.forEach(c => { fixedVals[c.id] = 0; fixedIds[c.id] = null })
  customs.value = []

  rows.forEach(r => {
    if (r.category === CUSTOM_CAT_ID) {
      customs.value.push({ ...r })            // id･label･amount･date
    } else {
      fixedVals[r.category] = r.amount
      fixedIds [r.category] = r.id
    }
  })
  if (!customs.value.length) addRow()
}

/* ---------- 保存 ---------- */
async function save () {
  const tasks = []

  // 固定費
  fixedCats.value.forEach(cat => {
    const amt = Number(fixedVals[cat.id] || 0)
    if (amt > 0) {
      if (fixedIds[cat.id]) {
        tasks.push(updateExpenseEntry(fixedIds[cat.id], { amount: amt }))
      } else {
        tasks.push(
          createExpenseEntry({
            date: date.value, store: props.storeId,
            category: cat.id, amount: amt, label: cat.name,
          })
        )
      }
    } else if (fixedIds[cat.id]) {
      tasks.push(deleteExpenseEntry(fixedIds[cat.id]))
    }
  })

  // カスタム
  customs.value.forEach(r => {
    if (!r.label.trim() || !r.amount) return     // 空行スキップ

    const payload = {
      date: r.date, store: props.storeId,
      category: CUSTOM_CAT_ID, amount: +r.amount, label: r.label.trim(),
    }
    r.id
      ? tasks.push(updateExpenseEntry(r.id, payload))
      : tasks.push(createExpenseEntry(payload))
  })

  await Promise.all(tasks)
  alert('保存しました！')
  await load()
}

/* ---------- 初期化 & ウォッチ ---------- */
onMounted(load)
watch(date, load)
</script>

<template>
  <div class="container-fluid">
    <!-- <h2 class="h4 mb-3">経費入力</h2> -->

    <!-- 日付 -->
    <div class="d-flex align-items-center gap-3 mb-3">
      <label class="mb-0">対象日</label>
      <input
        v-model="date"
        type="date"
        class="form-control"
        style="max-width:200px;"
      >
    </div>

    <!-- 固定費 ------------------------------------------------ -->

    <div class="card mb-4">
      <h2 class="card-header p-0">
        <button
          class="btn btn-link w-100 text-start collapsed"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#fixCollapse"
          aria-expanded="false"
          aria-controls="fixCollapse"
        >
          固定費
        </button>
      </h2>
      <div
        id="fixCollapse"
        class="collapse"
        aria-labelledby="fixCollapse"
      >
        <div
          v-for="cat in fixedCats"
          :key="cat.id"
          class="row g-2 align-items-center"
        >
          <label class="col-sm-3 col-form-label">{{ cat.name }}</label>
          <div class="col-sm-5">
            <input
              v-model.number="fixedVals[cat.id]"
              type="number"
              min="0"
              class="form-control"
              placeholder="0"
            >
          </div>
          <span class="col-auto">円</span>
        </div>
      </div>
    </div>

    <!-- カスタム ------------------------------------------------ -->
    <div class="card mb-4">
      <div class="card-header fw-bold d-flex justify-content-between align-items-center">
        <span>カスタム経費</span>
        <button
          class="btn btn-sm btn-success"
          @click="addRow"
        >
          ＋ 行追加
        </button>
      </div>
      <div class="card-body p-0">
        <table class="table mb-0 align-middle">
          <thead>
            <tr>
              <th style="width:45%">
                ラベル
              </th><th style="width:25%">
                金額
              </th><th style="width:25%">
                日付
              </th><th />
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(r,i) in customs"
              :key="i"
            >
              <td>
                <input
                  v-model="r.label"
                  class="form-control"
                >
              </td>
              <td class="d-flex align-items-center">
                <input
                  v-model.number="r.amount"
                  type="number"
                  min="0"
                  class="form-control"
                >
                <span class="ms-1">円</span>
              </td>
              <td>
                <input
                  v-model="r.date"
                  type="date"
                  class="form-control"
                >
              </td>
              <td>
                <button
                  class="btn btn-outline-danger btn-sm"
                  @click="removeRow(i,r)"
                >
                  ×
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 保存 -->
    <div class="text-end">
      <button
        class="btn btn-primary"
        @click="save"
      >
        保存
      </button>
    </div>
  </div>
</template>

<style scoped>
table input[type='number']::-webkit-outer-spin-button,
table input[type='number']::-webkit-inner-spin-button{ -webkit-appearance:none; margin:0 }
</style>
