/* src/composables/useBillData.js */
import { ref, watch } from 'vue'
import { useBills } from '@/stores/useBills'
import { fetchMasters, fetchCasts, fetchTables } from '@/api'

export function useBillData (billIdRef) {
/* ───── 安全な空オブジェクト ───── */
  const emptyBill = () => ({
    id              : '',
    items           : [],
    table           : { id:null, number:'', store:null },
    nominated_casts : [],
    inhouse_casts   : [],
    service_rate    : 0.10,
    tax_rate        : 0.10,
  })

/* ───── reactive 変数 ───── */
  const bills      = useBills()
  const bill       = ref(emptyBill())
  const masters    = ref([])
  const casts      = ref([])
  const tables     = ref([])
  const isLoading  = ref(false)

/* ───── 一括ロード ───── */
  async function load () {
    const id = billIdRef.value
    if (!id) return

    bill.value = emptyBill()        // ★ 空に戻してから読み込み
    isLoading.value = true

    try {
      /* ① 伝票本体 */
      await bills.open(id)
      const b = bills.current || {}

      bill.value = {
        ...emptyBill(),
        ...b,
        items           : Array.isArray(b.items)            ? [...b.items]            : [],
        nominated_casts : Array.isArray(b.nominated_casts)  ? [...b.nominated_casts]  : [],
        inhouse_casts   : Array.isArray(b.inhouse_casts)    ? [...b.inhouse_casts]    : [],
        service_rate    : Number(b.service_rate ?? 0.10),
        tax_rate        : Number(b.tax_rate    ?? 0.10),
      }

      /* ② マスタ類（同一店舗） */
      const storeId = bill.value.table?.store ?? 1
      const [m, c, t] = await Promise.all([
        fetchMasters(storeId),
        fetchCasts(storeId),
        fetchTables(storeId),
      ])
      masters.value = m ?? []
      casts.value   = c ?? []
      tables.value  = t ?? []
    } finally {
      isLoading.value = false
    }
  }

/* ───── billId 変更で自動ロード ───── */
  watch(billIdRef, id => { if (id) load() }, { immediate: true })

/* ───── 外部用 ───── */
  return { bill, masters, casts, tables, isLoading, refresh: load }
}
