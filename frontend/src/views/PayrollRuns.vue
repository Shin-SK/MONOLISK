<!-- frontend/src/views/PayrollRuns.vue -->
<script setup>
import { onMounted, ref } from "vue";
import { api } from "@/api";
import PersonnelExpensesSection from "@/components/expenses/PersonnelExpensesSection.vue";

const from = ref("");
const to = ref("");
const note = ref("");

const preview = ref(null);
const loading = ref(false);
const exporting = ref(false);
const error = ref("");

// 明細の開閉管理
const openCastIds = ref(new Set());
function isOpen(id) {
  return openCastIds.value.has(id);
}
function toggle(id) {
  const s = openCastIds.value;
  if (s.has(id)) s.delete(id); else s.add(id);
  // 反応性のため新しいSetに置き換え
  openCastIds.value = new Set(s);
}

// 表示ユーティリティ
function yen(n) {
  const num = Number(n || 0);
  return "¥" + num.toLocaleString("ja-JP");
}
function minToHours(min) {
  const m = Number(min || 0);
  return (m / 60).toFixed(2);
}
function safeArray(x) {
  return Array.isArray(x) ? x : [];
}
function sum(arr, key) {
  return safeArray(arr).reduce((a, v) => a + Number(v?.[key] || 0), 0);
}
function sumBill(billRows, key) {
  return safeArray(billRows).reduce((a, v) => a + Number(v?.[key] || 0), 0);
}
function fmtDateTime(dt) {
  if (!dt) return "";
  // 簡易フォーマット: YYYY-MM-DD HH:mm 風
  try {
    const d = new Date(dt);
    if (isNaN(d.getTime())) return String(dt);
    const y = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const mi = String(d.getMinutes()).padStart(2, "0");
    return `${y}-${mm}-${dd} ${hh}:${mi}`;
  } catch (_) {
    return String(dt);
  }
}

function pickError(e) {
  return e?.response?.data?.detail || e?.message || "エラー";
}

function buildParams() {
  const p = {};
  if (from.value) p.from = from.value;
  if (to.value) p.to = to.value;
  if (note.value) p.note = note.value;
  return p;
}

async function loadPreview() {
  error.value = "";
  loading.value = true;
  try {
    const res = await api.get("/api/billing/payroll/runs/preview/", { params: buildParams() });
    preview.value = res.data;

    // 省略時はサーバがデフォルト期間を返すので、UI側にも反映
    if (preview.value?.range?.from && !from.value) from.value = preview.value.range.from;
    if (preview.value?.range?.to && !to.value) to.value = preview.value.range.to;
  } catch (e) {
    preview.value = null;
    error.value = pickError(e) || "プレビュー取得に失敗しました";
  } finally {
    loading.value = false;
  }
}

async function exportCsv() {
  // TODO: 本来の出力APIに接続。ひとまずノーオペでエラーを出さない
  exporting.value = true;
  try {
    // 例: await api.post("/api/billing/payroll/runs/export/", buildParams())
    console.debug("exportCsv invoked", buildParams());
  } catch (e) {
    error.value = pickError(e) || "CSV出力に失敗しました";
  } finally {
    exporting.value = false;
  }
}

onMounted(loadPreview);
</script>

<template>
  <div>
    <!-- プレビュー入力 -->
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <div class="py-3 fw-bold">給与締めプレビュー</div>
      </div>
      <div class="card-body">
        <div class="row g-3">
          <div class="col-12 col-md-4">
            <label class="form-label small">開始日</label>
            <input type="date" class="form-control" v-model="from" />
          </div>
          <div class="col-12 col-md-4">
            <label class="form-label small">終了日</label>
            <input type="date" class="form-control" v-model="to" />
          </div>
          <div class="col-12 col-md-4">
            <label class="form-label small">備考（任意）</label>
            <input type="text" class="form-control" v-model="note" placeholder="例）12月分/再出力 など" />
          </div>
          <div class="col-12 col-md-6">
            <button class="btn btn-sm btn-primary w-100" @click="loadPreview" :disabled="loading">
              プレビュー
            </button>
          </div>
          <div class="col-12 col-md-6">
            <button class="btn btn-sm btn-outline-secondary w-100" @click="loadPreview" :disabled="loading">
              再読込
            </button>
          </div>
        </div>

        <div class="mt-3" v-if="preview">
          <div class="d-flex flex-wrap gap-2 align-items-center">
            <span class="badge text-bg-light">
              対象期間：{{ preview.range.from }} ～ {{ preview.range.to }}
            </span>

            <span v-if="preview.overlap" class="badge text-bg-warning">
              注意：過去の締め期間と重複しています（出力は可能）
            </span>

            <span v-if="!preview.overlap" class="badge text-bg-success">
              重複なし
            </span>
          </div>

          <div class="text-muted small mt-2">
            ※締め後に伝票・勤怠が修正されても、この出力結果は自動更新しません。必要なら再出力してください。
          </div>
        </div>

        <div class="alert alert-danger mt-3 mb-0" v-if="error">
          {{ error }}
        </div>
      </div>
    </div>

    <!-- summary table -->
    <div class="card mb-3" v-if="preview">
      <div class="card-header d-flex justify-content-between align-items-center">
        <div class="py-3 fw-bold">給与集計（プレビュー）</div>
      </div>

      <div class="table-responsive">
        <table class="table table-striped table-hover mb-0">
          <thead>
            <tr>
              <th>源氏名</th>
              <th class="text-end">勤務時間(h)</th>
              <th class="text-end">時給合計</th>
              <th class="text-end">売上</th>
              <th class="text-end">バック合計</th>
              <th class="text-end">給与合計</th>
              <th class="text-center">明細</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in preview.summary" :key="row.cast_id">
              <tr>
                <td class="fw-bold">{{ row.stage_name }}</td>
                <td class="text-end">{{ minToHours(row.worked_min) }}</td>
                <td class="text-end">{{ yen(row.hourly_pay) }}</td>
                <td class="text-end">{{ yen(row.sales_total || 0) }}</td>
                <td class="text-end">{{ yen(row.commission) }}</td>
                <td class="text-end fw-bold">{{ yen(row.total) }}</td>
                <td class="text-center">
                  <button class="btn btn-sm btn-outline-primary" @click="toggle(row.cast_id)">
                    {{ isOpen(row.cast_id) ? "閉じる" : "開く" }}
                  </button>
                </td>
              </tr>

              <!-- details row -->
              <tr v-if="isOpen(row.cast_id)">
                <td colspan="7" class="bg-light">
                  <div class="small text-muted mb-2">
                    伝票明細（売上→バック根拠）
                  </div>

                  <div v-if="safeArray(row.bill_rows).length === 0" class="text-muted">
                    この期間の伝票がありません
                  </div>

                  <div v-for="b in safeArray(row.bill_rows)" :key="b.bill_id" class="mb-3">
                    <div class="d-flex flex-wrap gap-2 align-items-center">
                      <span class="badge text-bg-secondary">伝票ID: {{ b.bill_id }}</span>
                      <span class="badge text-bg-light">締め: {{ fmtDateTime(b.closed_at) }}</span>
                      <span class="badge text-bg-light">売上: {{ yen(b.sales || 0) }}</span>
                      <span class="badge text-bg-light">バック: {{ yen(b.back || 0) }}</span>
                    </div>

                    <!-- items -->
                    <div class="table-responsive mt-2">
                      <table class="table table-sm table-bordered mb-0">
                        <thead>
                          <tr>
                            <th>ID</th>
                            <th>品目</th>
                            <th class="text-end">単価</th>
                            <th class="text-end">数量</th>
                            <th class="text-end">小計</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(it, idx) in safeArray(b.items)" :key="`${b.bill_id}-${idx}`">
                            <td>{{ it.id ? `#${it.id}` : `#${idx + 1}` }}</td>
                            <td>{{ it.name }}</td>
                            <td class="text-end">{{ yen(it.price) }}</td>
                            <td class="text-end">{{ it.qty }}</td>
                            <td class="text-end">{{ yen((it.price || 0) * (it.qty || 0)) }}</td>
                          </tr>
                          <tr v-if="safeArray(b.items).length === 0">
                            <td colspan="5" class="text-center text-muted">明細がありません</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <!-- per-cast totals inside details -->
                  <div class="text-end small">
                    <span class="me-3">伝票売上合計: {{ yen(sumBill(row.bill_rows, "sales")) }}</span>
                    <span>伝票バック合計: {{ yen(sumBill(row.bill_rows, "back")) }}</span>
                  </div>
                </td>
              </tr>
            </template>

            <tr v-if="preview.summary.length === 0">
              <td colspan="7" class="text-center text-muted py-4">
                対象期間のデータがありません
              </td>
            </tr>
          </tbody>
          <tfoot v-if="preview.summary.length">
            <tr class="table-light">
              <th>合計</th>
              <th class="text-end">{{ minToHours(sum(preview.summary, "worked_min")) }}</th>
              <th class="text-end">{{ yen(sum(preview.summary, "hourly_pay")) }}</th>
              <th class="text-end">{{ yen(sum(preview.summary, "sales_total")) }}</th>
              <th class="text-end">{{ yen(sum(preview.summary, "commission")) }}</th>
              <th class="text-end">{{ yen(sum(preview.summary, "total")) }}</th>
              <th></th>
            </tr>
          </tfoot>
        </table>
      </div>

      <div class="card-footer py-4">
        <button class="btn btn-success btn-sm w-100" @click="exportCsv" :disabled="exporting || !preview">
          <span v-if="exporting" class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>
          締めてCSV出力
        </button>
      </div>
    </div>

    <!-- Personnel Expenses (Component) -->
    <PersonnelExpensesSection
      v-if="preview && preview.run_id"
      :run-id="preview.run_id"
      :range-from="preview.range.from"
      :range-to="preview.range.to"
      :allow-attach="true"
    />

    <!-- loading -->
    <div class="text-center text-muted" v-if="loading">
      <span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>
      読み込み中…
    </div>
  </div>
</template>



<style scoped lang="scss">

.table-responsive{
    th, td{
        white-space: nowrap;
    }
}

.modal.show {
  display: block !important;
}

.modal-backdrop.show {
  opacity: 0.5;
}
    
</style>