<!-- src/views/CastShiftList.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import {
    fetchCastShifts,     // きょうの打刻取得
    createCastShift,     // シフト行が無いキャスト用
    castCheckIn,
    castCheckOut,
    deleteCastShift,
    getBillingCasts,     // 全キャスト一覧
} from '@/api'
import { yen } from '@/utils/money'

/* ------- 状態 ------- */
const rows = ref([])   // { cast:{…}, shift:{…}|null } の配列

/* ------- データロード ------- */
async function load () {
    const [casts, shifts] = await Promise.all([
        getBillingCasts(),                               // 全キャスト
        fetchCastShifts({ date: dayjs().format('YYYY-MM-DD') }),
    ])
    const shiftMap = Object.fromEntries(shifts.map(s => [s.cast.id, s]))
    rows.value = casts.map(c => ({ cast: c, shift: shiftMap[c.id] || null }))
}

/* ------- 操作 ------- */
async function ensureShift (row) {
    if (!row.shift) {
        row.shift = await createCastShift({
            cast_id: row.cast.id,
            store_id: row.cast.store,   // FK が null の場合は適宜変更
        })
    }
}

async function checkIn (row) {
    await ensureShift(row)
    if (!row.shift.clock_in) {
        await castCheckIn(row.shift.id)
        await load()
    }
}

async function checkOut (row) {
    if (row.shift && !row.shift.clock_out) {
        await castCheckOut(row.shift.id)
        await load()
    }
}

async function removeShift (row) {
    if (row.shift && confirm('本当に削除しますか？')) {
        await deleteCastShift(row.shift.id)
        row.shift = null
        await load()
    }
}

onMounted(load)
</script>

<template>
    <div>
        <h2 class="mb-3">キャスト出勤一覧</h2>

        <table class="table table-sm">
            <thead>
                <tr>
                    <th>キャスト</th>
                    <th>出勤</th>
                    <th>退勤</th>
                    <th>勤務時間</th>
                    <th>時給</th>
                    <th class="text-end">操作</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="row in rows" :key="row.cast.id">

                    <!-- 詳細ページリンク -->
                    <td>
						<RouterLink
						:to="{ name: 'cast-shift-page', params: { id: row.cast.id } }">
						{{ row.cast.stage_name }}
						</RouterLink>
                    </td>

                    <td>{{ row.shift?.clock_in ? dayjs(row.shift.clock_in).format('HH:mm') : '–' }}</td>
                    <td>{{ row.shift?.clock_out ? dayjs(row.shift.clock_out).format('HH:mm') : '–' }}</td>

                    <td>
                        <span v-if="row.shift?.worked_min">
                            {{ (row.shift.worked_min / 60).toFixed(2) }} h
                        </span>
                        <span v-else>–</span>
                    </td>

                    <td>{{ yen(row.shift?.hourly_wage_snap || row.cast.hourly_wage || 0) }}</td>

<!-- CastShiftList.vue の “操作” 列だけ差し替え -->
<td class="text-end">
  <!-- 出勤 -->
  <button
    class="btn btn-sm btn-primary me-1"
    :disabled="!!row.shift?.clock_in"
    @click="checkIn(row)"
  >
    出勤
  </button>

  <!-- 退勤 -->
  <button
    class="btn btn-sm btn-danger me-1"
    :disabled="!row.shift || !!row.shift.clock_out"
    @click="checkOut(row)"
  >
    退勤
  </button>

  <!-- 削除 -->
  <button
    class="btn btn-sm btn-outline-secondary"
    :disabled="!row.shift"
    @click="removeShift(row)"
  >
    削除
  </button>
</td>

                </tr>
            </tbody>
        </table>
    </div>
</template>
