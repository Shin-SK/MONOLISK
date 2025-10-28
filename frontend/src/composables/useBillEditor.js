// src/composables/useBillEditor.js
import { ref, computed, toRef, onMounted, watch } from 'vue'
import { useTables }  from '@/stores/useTables'
import { useMasters } from '@/stores/useMasters'
import { useCasts }   from '@/stores/useCasts'
import { useCustomers } from '@/stores/useCustomers'
import {
  addBillItem,
  updateBillCustomers,
  updateBillTable,
  updateBillCasts,
  setBillDohan,
  api,
} from '@/api'


export default function useBillEditor(billObjRef){
  const bill = toRef(billObjRef)
  const isNew = computed(() => !bill.value?.id)
  const storeId = computed(() => bill.value?.table?.store ?? '')

  /* stores */
  const tablesStore  = useTables()
  const mastersStore = useMasters()
  const castsStore   = useCasts()

  const tables  = computed(() => Array.isArray(tablesStore.list)  ? tablesStore.list.filter(Boolean)  : [])
  const masters = computed(() => Array.isArray(mastersStore.list) ? mastersStore.list.filter(Boolean) : [])
  const casts   = computed(() => Array.isArray(castsStore.list)   ? castsStore.list.filter(Boolean)   : [])

  /* ===== Basics ===== */
  const tableId = ref(bill.value?.table?.id ?? null)
  const pax     = ref(1)
  const pending = ref([])


  /* ===== Order（カテゴリタブ／品目／提供者） ===== */
  const catCode = (m) => (typeof m?.category === 'string' ? m.category : m?.category?.code)
  const orderCatOptions = computed(() => {
    const list = Array.isArray(masters.value) ? masters.value : []
    const shown = list.filter(m => m?.category && m.category?.show_in_menu === true)
    const codes = [...new Set(shown.map(m => catCode(m)))]
    return codes.map(code => {
      const first = shown.find(m => catCode(m) === code)
      const label = (typeof first?.category === 'object' ? first.category.name : code)
      return { value: code, label }
    })
  })
  const selectedOrderCat = ref(null)
  watch(orderCatOptions, (opts) => {
    if (!selectedOrderCat.value && opts.length) selectedOrderCat.value = opts[0].value
  }, { immediate: true })

  const orderMasters = computed(() => {
    const list = Array.isArray(masters.value) ? masters.value : []
    return list
      .filter(m => catCode(m) === selectedOrderCat.value)
      .map(m => ({
        id: m.id,
        name: m.name,
        // 子（OrderPanelSP）は m.price を表示しているのでここで揃える
        price: m.price_regular ?? null,
      }))
  })

  const servedByCastId = ref(null)   // 提供者（未指定はnull）
  function addPending(masterId, qty = 1){
    if (!masterId) return
    pending.value.push({
      master_id: masterId,
      qty,
      cast_id: servedByCastId.value || null,
    })
  }

  
  const customerName = computed(() => bill.value?.customer_display_name || '')
  const showCustModal = ref(false)
  const activeCustId  = ref(null)

  // ▼ SP: インライン検索用
  const customersStore = useCustomers()
  const custQuery    = ref('')
  const custResults  = ref([])
  const custLoading  = ref(false)

  async function searchCustomers(q){
    custQuery.value = q ?? ''
    custLoading.value = true
    try{
      if (customersStore?.search) {
        const res = await customersStore.search(custQuery.value)
        custResults.value = Array.isArray(res)
          ? res.filter(x => x && x.id != null)
          : Array.isArray(customersStore.list)
            ? customersStore.list.filter(x => x && x.id != null)
            : []
      } else {
        const { data } = await api.get('customers/', { params:{ q: custQuery.value } })
        const arr = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
        custResults.value = arr.filter(x => x && x.id != null)
      }
    }catch(e){
      console.error(e); custResults.value = []
    }finally{
      custLoading.value = false
    }
  }

  function resetCustomerSearch(){ custQuery.value=''; custResults.value=[]; custLoading.value=false }
  async function pickCustomerInline(cust){ await handleCustPicked(cust); resetCustomerSearch() }

  const COURSE_CATS = ['setMale','setVip','setFemale']
  const courseOptions = computed(() =>
    COURSE_CATS.map(code => {
      const m = masters.value.find(v => catCode(v) === code)
      return m ? { id: m.id, code: m.code, label: m.name } : null
    }).filter(Boolean)
  )

  function openCustomer(id=null){ activeCustId.value = id; showCustModal.value = true }
  function clearCustomer(){
    if(!bill.value) return
    bill.value.customers = []
    bill.value.customer_display_name = ''
    if (!isNew.value) {
      updateBillCustomers(bill.value.id, []).catch(e => { console.error(e); alert('顧客更新に失敗しました') })
    }
  }
  async function handleCustPicked(cust){
    const ids = new Set((bill.value.customers ?? []).map(v => typeof v==='object' ? v.id : v))
    ids.add(cust.id)
    bill.value.customers = [...ids]
    bill.value.customer_display_name = cust.alias?.trim() || cust.full_name || `#${cust.id}`
    if (!isNew.value) {
      try { await updateBillCustomers(bill.value.id, bill.value.customers) }
      catch(e){ console.error(e); alert('顧客更新に失敗しました') }
    }
    showCustModal.value = false
  }
  function handleCustSaved(cust){
    const ids = new Set(bill.value.customers ?? [])
    ids.add(cust.id)
    bill.value.customers = [...ids]
    bill.value.customer_display_name = cust.alias?.trim() || cust.full_name || `#${cust.id}`
    showCustModal.value = false
  }

  async function chooseCourse(opt){
    if (!opt) return { updated:false }
    if (isNew.value){
      pending.value.push({ master_id: opt.id, qty: pax.value, cast_id: null })
      return { pending:true, updated:false }
    }
    const newItem = await addBillItem(bill.value.id, { item_master: opt.id, qty: pax.value })
    bill.value.items = bill.value.items || []
    bill.value.items.push(newItem)

    const currentTableId = bill.value.table?.id ?? bill.value.table ?? null
    if (tableId.value !== currentTableId) {
      await updateBillTable(bill.value.id, tableId.value)
    }
    return { pending:false, updated:true, item:newItem }
  }

  /* ===== Casts（ドラッグ無し／ボタン操作） ===== */
  const mainIds    = ref([])           // 本指名
  const freeIds    = ref([])           // フリー着席
  const inhouseIds = ref([])           // 場内（フリーの部分集合）
  const castKeyword = ref('')
  const onDutySet  = ref(new Set())    // 本日出勤中
  const dohanIds = ref([])

  // 初期化：既存伝票のstays → 各配列へ
  function initCastsFromBill(){
    const b = bill.value
    if (!b) return
    const active = (b.stays ?? []).filter(s => !s.left_at)
    mainIds.value    = active.filter(s => s.stay_type === 'nom').map(s => s.cast.id)
    const freeRaw    = active.filter(s => s.stay_type === 'free').map(s => s.cast.id)
    const inRaw      = active.filter(s => s.stay_type === 'in').map(s => s.cast.id)
    inhouseIds.value = [...new Set(inRaw)]
    freeIds.value    = [...new Set([...freeRaw, ...inRaw])]
    dohanIds.value = active.filter(s => s.stay_type === 'dohan').map(s => s.cast.id)
  }

// 現在の配席一覧（UI表示用）
// 現在の配席一覧（UI表示用）
// currentCasts：main → dohan → free/in の順で、重複なし
const currentCasts = computed(() => {
  const list = []

  // main（赤）
  for (const id of mainIds.value) {
    if (dohanIds.value.includes(id)) continue // 同伴優先で除外
    const c = casts.value.find(x => x.id === id)
    if (c) list.push({
      ...c,
      name   : c.stage_name ?? c.name ?? '',
      avatar : c.avatar_url ?? c.avatar ?? '',
      kind      : 'nom',
      stay_type : 'nom',         // ← ★ これを必ず持たせる
      inhouse: false
    })
  }

  // dohan（グレー＝secondary）
  for (const id of dohanIds.value) {
    const c = casts.value.find(x => x.id === id)
    if (c) list.push({
      ...c,
      name   : c.stage_name ?? c.name ?? '',
      avatar : c.avatar_url ?? c.avatar ?? '',
      kind      : 'dohan',
      stay_type : 'dohan',
      inhouse: false,
      dohan  : true
    })
  }

  // free/in（緑/青）… main/dohan と重複しない
  const others = new Set([...freeIds.value, ...inhouseIds.value])
  for (const id of others) {
    if (mainIds.value.includes(id) || dohanIds.value.includes(id)) continue
    const c = casts.value.find(x => x.id === id)
    if (c) {
      const isIn = inhouseIds.value.includes(id)
      list.push({
        ...c,
        name   : c.stage_name ?? c.name ?? '',
        avatar : c.avatar_url ?? c.avatar ?? '',
        kind      : 'free',
        inhouse   : isIn,
        stay_type : isIn ? 'in' : 'free',   // ← ★ 追加
      })
    }
  }

  return list
})


  // ベンチ（未選択）
const benchCasts = computed(() => {
  const chosen = new Set([...mainIds.value, ...freeIds.value, ...inhouseIds.value, ...dohanIds.value])
  const kw = castKeyword.value.trim().toLowerCase()
  const list = Array.isArray(casts.value) ? casts.value : []
  return list.filter(c => {
    if (!c || c.id == null) return false
    if (chosen.has(c.id)) return false
    if (!kw) return true
    return (c.stage_name || '').toLowerCase().includes(kw)
  })
})

  // 同期（既存伝票のみ）
  async function syncCasts(){
    if (isNew.value) return
    await updateBillCasts(bill.value.id, {
      nomIds:  [...mainIds.value],
      inIds:   [...inhouseIds.value],
      freeIds: [...freeIds.value],
      dohanIds: [...dohanIds.value],
    })
  }

  // 操作：追加/変更/削除（ドラッグ無し）
  function ensureFree(id){
    if (!freeIds.value.includes(id)) freeIds.value.push(id)
  }
  async function setFree(id){
    ensureFree(id)
    // inhouse外す
    inhouseIds.value = inhouseIds.value.filter(x => x !== id)
    await syncCasts()
  }
  async function setInhouse(id){
    ensureFree(id)
    if (!inhouseIds.value.includes(id)) inhouseIds.value.push(id)
    await syncCasts()
  }

  async function setDohan(id){
    const billId = bill.value?.id
    // 新規（未作成）なら他ボタンと同じ：ローカルだけ更新して終了
    if (!billId) {
      mainIds.value    = mainIds.value.filter(x => x !== id)
      inhouseIds.value = inhouseIds.value.filter(x => x !== id)
      if (!dohanIds.value.includes(id)) dohanIds.value.push(id)
      return
    }
    // 既存伝票はサーバに反映
    try {
      await setBillDohan(billId, id)
      mainIds.value    = mainIds.value.filter(x => x !== id)
      inhouseIds.value = inhouseIds.value.filter(x => x !== id)
      if (!dohanIds.value.includes(id)) dohanIds.value.push(id)
    } catch (e) {
      console.error(e)
      alert('同伴の設定に失敗しました')
    }
  }


  async function setMain(id){
    if (!mainIds.value.includes(id)) mainIds.value.push(id)
    ensureFree(id)
    await syncCasts()
  }
  async function removeCast(id){
    mainIds.value    = mainIds.value.filter(x => x !== id)
    freeIds.value    = freeIds.value.filter(x => x !== id)
    inhouseIds.value = inhouseIds.value.filter(x => x !== id)
    dohanIds.value   = dohanIds.value.filter(x => x !== id)
    await syncCasts()
  }

  onMounted(async () => {
    try {
      await Promise.all([
        tablesStore.fetch(storeId.value),
        mastersStore.fetch(storeId.value),
        castsStore.fetch(storeId.value),
      ])
      // 出勤情報（任意）
      const today = new Date().toISOString().slice(0,10)
      const { data: shifts } = await api.get('billing/cast-shifts/', {
        params: { from: today, to: today, store: storeId.value }
      })
      onDutySet.value = new Set(
        shifts.filter(s => s.clock_in && !s.clock_out).map(s => s.cast.id)
      )
      initCastsFromBill()
    } catch(e) { console.error('fetch failed', e) }
  })

  return {
    /* Basics */
    isNew, tables, masters, tableId, pax, pending,
    courseOptions, customerName,
    showCustModal, activeCustId,
    openCustomer, clearCustomer, handleCustPicked, handleCustSaved,
    chooseCourse,

    /* Casts */
    casts, onDutySet, castKeyword,
    mainIds, freeIds, inhouseIds,
    currentCasts, benchCasts,
    setFree, setInhouse, setMain, setDohan, removeCast,

    // Order

    orderCatOptions, selectedOrderCat, orderMasters,
    servedByCastId, addPending,
    pending,  // 既存をここでも返しておく（保存で使う）

    // SP: 顧客インライン検索
    custQuery, custResults, custLoading, searchCustomers, resetCustomerSearch, pickCustomerInline,


  }
}
