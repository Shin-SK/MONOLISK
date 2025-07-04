<!-- src/views/DriverShift.vue -->
<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getDriverShift,
  getDriver,
  getAllDriverShifts,
  clockIn  as apiClockIn,
  clockOut as apiClockOut
} from '@/api'
import dayjs from 'dayjs'
import InputNumber from '@/components/InputNumber.vue'

/* ----- ルート param  ----- */
const route     = useRoute()
const router    = useRouter()   
const shiftId  = computed(() =>
  Number(route.params.shiftId ?? route.params.id) || null)
const myDriverId = null               // ←ログイン中ドライバーIDを入れるならここ
const driverId  = computed(() => shift.driver)   // 取得後に使う用
const isReadonly = computed(() =>       // 自分以外のシフトは閲覧のみ
  driverId.value && myDriverId && driverId.value !== myDriverId
)
const driverParam = computed(() => Number(route.params.driverId) || null)
const hasClockedIn  = computed(() => !!shift.clock_in_at)
const hasClockedOut = computed(() => !!shift.clock_out_at)
const driverName = computed(() => shift.driver_name || '')

/* ----- ドライバー情報 ----- */
const driverInfo = ref(null)  
const clockInAtInput = ref(dayjs().format('YYYY-MM-DDTHH:mm')) 


/* ----- state ----- */
const shift = reactive({
  id: null,
  float_start : 10000,
  clock_in_at : null,
  total_received : 0,
  used_float     : 0,
  expenses       : 0,
  actual_cash    : 0,
  actual_deposit : 0,
  float_end      : 10000,
  diff_reason    : '',
  manager_checked: false,
})

/* ----- プリセット ----- */
const presets = [0, 5_000, 10_000]

/* ----- 計算 ----- */
const expectedDeposit = computed(
  () => shift.total_received - shift.used_float - shift.expenses
)
const expectedCash = computed(
  () => expectedDeposit.value + shift.float_end          // ← 「+」 を補完
)
const diff = computed(() => shift.actual_cash - expectedCash.value)
const disableSubmit = computed(
  () => diff.value !== 0 && !shift.diff_reason.trim()
)
const autoFields = computed(() => ([
  { label:'総受取金', value:shift.total_received },
  { label:'使用釣り銭', value:shift.used_float },
  { label:'計算上の入金額', value:expectedDeposit.value },
  { label:'計算上の所持金', value:expectedCash.value },
]))

/* ----- API ----- */
async function fetchShift () {
  if (shiftId.value) {
    const data = await getDriverShift(shiftId.value)
    Object.assign(shift, data)
  } else if (driverParam.value) {
    const list = await getAllDriverShifts({
      date: dayjs().format('YYYY-MM-DD'),
      driver: driverParam.value,
    })
    if (list.length) {
      Object.assign(shift, list[0])
    } else {
      // レコードなし → 名前だけ取得して表示用に保存
      const d = await getDriver(driverParam.value)
      shift.driver_name = d.user_name || d.name   // ←ここに詰めちゃえば OK
      shift.driver = driverParam.value
    }
  }
}
async function doClockIn () {
   // ① STAFF 画面なら driverParam（URL の /driver/123 部分）を使う
   const targetId =
         driverParam.value     // /driver-shifts/driver/<id>
      || shift.driver
      || myDriverId           // ログイン中ドライバー本人

   if (!targetId) {
     return alert('ドライバーIDが特定できません')
   }
  const data = await apiClockIn(targetId, {
    float_start: shift.float_start,
    at:          clockInAtInput.value + ':00',  // ISO8601 に
  })
   Object.assign(shift, data)
   driverInfo.value = await getDriver(data.driver)

   router.push('/driver-shifts')
 }

async function doClockOut () {
   if (isReadonly.value) return
   if (!shift.id) {
      alert('まず出勤を登録してください')
      return
   }
  await apiClockOut(shift.id, {
    expenses       : shift.expenses,
    actual_cash    : shift.actual_cash,
    actual_deposit : shift.actual_deposit,
    float_end      : shift.float_end,
    diff_reason    : shift.diff_reason,
    manager_checked: shift.manager_checked,
  })
  alert('退勤を登録しました')
  await fetchShift()
  router.push('/driver-shifts')
}

onMounted(async () => {
  await fetchShift()
  if (shift.clock_in_at) {
    clockInAtInput.value = dayjs(shift.clock_in_at)
                         .format('YYYY-MM-DDTHH:mm')
  }
})
</script>

<template>
  <div class="container-fluid py-4" style="max-width:720px">
    <h3 class="mb-4">
      {{ driverName ? `${driverName} 日報` : 'ドライバー日報' }}
      <template v-if="!driverName && driverId">#{{ driverId }}</template>
      <template v-else-if="!driverName">（今日・自分）</template>
    </h3>

    <!-- 出勤カード -->
    <div class="card mb-4">
      <div class="card-header bg-primary text-white">出勤</div>
      <div class="card-body">
<label class="form-label">出勤時刻</label>
<input type="datetime-local"
       v-model="clockInAtInput"
       class="form-control mb-3"
       :disabled="isReadonly">
        <label class="form-label">釣り銭</label>
        <div class="input-group mb-2">
          <input v-model.number="shift.float_start" type="number"
                 min="0" class="form-control" :readonly="isReadonly" />
          <span class="input-group-text">円</span>
        </div>
        <div class="btn-group mb-3">
          <button v-for="p in presets" :key="p"
                  class="btn btn-outline-secondary"
                  :disabled="isReadonly"
                  @click="shift.float_start = p">
            ¥{{ p.toLocaleString() }}
          </button>
        </div>
        <button class="btn btn-success w-100"
                :disabled="isReadonly"
                @click="doClockIn">
          {{ hasClockedIn ? '保存' : '出勤する' }}
        </button>
      </div>
    </div>

    <!-- 退勤カード -->
    <div class="card">
      <div class="card-header bg-secondary text-white d-flex justify-content-between">
        <span>退勤</span>
        <small v-if="shift.clock_in_at">
          {{ new Date(shift.clock_in_at).toLocaleTimeString() }} 出勤済み
        </small>
      </div>

      <div class="card-body">
        <div class="row g-3 mb-3">
          <div v-for="f in autoFields" :key="f.label" class="col-6">
            <div class="bg-light p-2 rounded">
              <div class="text-muted small">{{ f.label }}</div>
              <div class="fw-bold">¥{{ (+f.value).toLocaleString() }}</div>
            </div>
          </div>
        </div>

        <!-- 手入力 -->
        <div class="row g-3 mb-3">
          <InputNumber v-model="shift.expenses"       label="経費"          :readonly="isReadonly"/>
          <InputNumber v-model="shift.actual_cash"    label="実際の所持金" :readonly="isReadonly"/>
          <InputNumber v-model="shift.actual_deposit" label="店舗入金額"   :readonly="isReadonly"/>
          <InputNumber v-model="shift.float_end"      label="締め釣り銭"   :readonly="isReadonly"/>
        </div>

        <div class="alert" :class="diff===0 ? 'alert-success':'alert-danger'">
          差分：{{ diff.toLocaleString() }} 円
        </div>

        <div v-if="diff!==0" class="mb-3">
          <label class="form-label">差分理由</label>
          <textarea v-model="shift.diff_reason" rows="2"
                    class="form-control" :readonly="isReadonly"/>
        </div>

        <div class="form-check form-switch mb-3">
          <input type="checkbox" id="mgr" class="form-check-input"
                 v-model="shift.manager_checked" :disabled="isReadonly">
          <label class="form-check-label" for="mgr">店長チェック済み</label>
        </div>

        <button class="btn btn-primary w-100"
                :disabled="isReadonly || hasClockedOut || disableSubmit"
                @click="doClockOut">
          退勤する

        </button>
      </div>
    </div>
  </div>
</template>


<style scoped>
.text-muted { font-size:.875rem }
</style>
