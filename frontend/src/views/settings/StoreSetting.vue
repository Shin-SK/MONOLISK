<script setup>
import { ref, onMounted, computed } from 'vue'
import { api, getStores, getStore } from '@/api'

const stores = ref([])
const storeId = ref(null)
const form = ref({
  business_day_cutoff_hour: 6,
  service_rate_pct: 10,
  tax_rate_pct: 10,
  nom_pool_rate_pct: 50,
})
const saving = ref(false)
const saved  = ref(false)
const error  = ref('')

function pctFromDecimal(d){ return Math.round((+d || 0) * 100 * 100) / 100 }
function decFromPct(p){ return Math.round((+p || 0) * 100) / 100 / 100 }

async function load() {
  saved.value = false
  error.value = ''
  stores.value = await getStores()
  storeId.value = stores.value[0]?.id ?? null
  if (!storeId.value) return
  const s = await getStore(storeId.value)
  form.value = {
    business_day_cutoff_hour: s.business_day_cutoff_hour ?? 6,
    service_rate_pct: pctFromDecimal(s.service_rate),
    tax_rate_pct: pctFromDecimal(s.tax_rate),
    nom_pool_rate_pct: pctFromDecimal(s.nom_pool_rate),
  }
}

async function save() {
  if (!storeId.value) return
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    await api.patch(`billing/stores/${storeId.value}/`, {
      business_day_cutoff_hour: form.value.business_day_cutoff_hour,
      service_rate:  decFromPct(form.value.service_rate_pct),
      tax_rate:      decFromPct(form.value.tax_rate_pct),
      nom_pool_rate: decFromPct(form.value.nom_pool_rate_pct),
    })
    saved.value = true
  } catch (e) {
    error.value = e?.response?.data?.detail || '保存に失敗しました'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="card">
    <div class="card-body">
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <div v-if="saved" class="alert alert-success">保存しました</div>

      <div class="mb-3">
        <label class="form-label">営業日締め時刻（0–12）</label>
        <input type="number" class="form-control w-auto" v-model.number="form.business_day_cutoff_hour" min="0" max="12" />
        <div class="form-text">例: 6 = 朝6時締め（20:00–26:00 の運用向け）</div>
      </div>

      <div class="row g-3">
        <div class="col-sm-4">
          <label class="form-label">サービス料（%）</label>
          <input type="number" step="0.01" class="form-control" v-model.number="form.service_rate_pct" />
        </div>
        <div class="col-sm-4">
          <label class="form-label">消費税（%）</label>
          <input type="number" step="0.01" class="form-control" v-model.number="form.tax_rate_pct" />
        </div>
        <div class="col-sm-4">
          <label class="form-label">本指名プール率（%）</label>
          <input type="number" step="0.01" class="form-control" v-model.number="form.nom_pool_rate_pct" />
        </div>
      </div>

      <div class="mt-3">
        <button class="btn btn-primary" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>
