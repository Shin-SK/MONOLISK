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
import { enqueue } from '@/utils/txQueue'
import { useBills } from '@/stores/useBills'

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
  const tableId = ref(bill.value?.table?.id ?? bill.value?.table_id_hint ?? null)
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
  const selectedCustomerId = ref(null)  // 【フェーズ3】注文時の顧客ID
  
  // 【フェーズ3】castId と customerId を引数で受け取る
  function addPending(masterId, qty = 1, castId = null, customerId = null){
    if (!masterId) return
    pending.value.push({
      master_id: masterId,
      qty,
      cast_id: castId ?? servedByCastId.value ?? null,
      customer_id: customerId ?? selectedCustomerId.value ?? null,
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
  const selectedCustomer = computed(() => {
    const ids = bill.value?.customers || []
    if (!ids.length) return null
    const firstId = typeof ids[0] === 'object' ? ids[0].id : ids[0]
    return custResults.value.find(c => c.id === firstId) || null
  })

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
  // ★ 即ローカルで行を足す
  bill.value.items = bill.value.items || []
  bill.value.items.push({
    id: `tmp-${Date.now()}`, item_master: opt.id, qty: pax.value, price: null
  })
  // テーブル変更が必要なら裏送信
  const currentTableId = bill.value.table?.id ?? bill.value.table ?? null
  if (tableId.value !== currentTableId) {
    enqueue('updateBillTable', { id: bill.value.id, table_id: tableId.value })
  }
  // 明細追加を裏送信
  enqueue('addBillItem', { id: bill.value.id, item: { item_master: opt.id, qty: pax.value } })

  return { pending:false, updated:true }
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

  // Bill ID 切替時（同一テーブル再オープン等）で前回状態をクリア
  let _prevBillId = bill.value?.id || null
  watch(() => bill.value?.id, (newId) => {
    if (!newId || newId === _prevBillId) return
    // 基本配列を stays から再構築
    initCastsFromBill()
    // 一時注文/提供者など編集途中状態をクリア
    pending.value = []
    servedByCastId.value = null
    castKeyword.value = ''
    _prevBillId = newId
  })

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
    // ★ サーバ待ちなし：裏送信のみ
    const filteredFree = freeIds.value.filter(id => !mainIds.value.includes(id) && !dohanIds.value.includes(id))
    enqueue('updateBillCasts', {
      billId: bill.value.id,
      nomIds:  [...mainIds.value],
      inIds:   [...inhouseIds.value],
      freeIds: filteredFree,
      dohanIds:[...dohanIds.value],
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
    // 即ローカル反映（同伴は他カテゴリと排他）
    mainIds.value    = mainIds.value.filter(x => x !== id)
    inhouseIds.value = inhouseIds.value.filter(x => x !== id)
    freeIds.value    = freeIds.value.filter(x => x !== id)
    if (!dohanIds.value.includes(id)) dohanIds.value.push(id)

    if (isNew.value) return
    enqueue('updateBillCasts', {
      billId: bill.value.id,
      nomIds:  [...mainIds.value],
      inIds:   [...inhouseIds.value],
      freeIds: [...freeIds.value],
      dohanIds:[...dohanIds.value],
    })
  }



  async function setMain(id){
    if (!mainIds.value.includes(id)) mainIds.value.push(id)
    // ensureFree(id) を停止：freeIds との二重管理を避ける
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

  async function save(){
    // 楽観用の即時Billを構築
    const billsStore = useBills()
    const isNewBill  = !bill.value?.id
    const nowISO     = new Date().toISOString()

    // stays（本指名/場内/フリー/同伴）の現在値を作る
    const stays = []
    const mainSet  = new Set(mainIds.value || [])
    const dohanSet = new Set(dohanIds.value || [])

    // --- Diagnostics (Step 1) ---
    try {
      console.log('[diag save:start]', {
        billId: bill.value?.id ?? null,
        isNewBill,
        mainIds: [...mainIds.value],
        dohanIds: [...dohanIds.value],
        freeIds: [...freeIds.value],
        inhouseIds: [...inhouseIds.value],
        tableId: tableId.value,
      })
    } catch(e) { /* noop */ }

    // 本指名
    ;(mainIds.value || []).forEach(id => {
      stays.push({
        cast      : { id },
        stay_type : 'nom',
        entered_at: nowISO,
        left_at   : null,
      })
    })

    // 同伴
    ;(dohanIds.value || []).forEach(id => {
      stays.push({
        cast      : { id },
        stay_type : 'dohan',
        entered_at: nowISO,
        left_at   : null,
      })
    })

    // フリー / 場内 （本指名・同伴は除外）
    ;(freeIds.value || []).forEach(id => {
      if (mainSet.has(id) || dohanSet.has(id)) return
      const isIn = inhouseIds.value.includes(id)
      stays.push({
        cast      : { id },
        stay_type : isIn ? 'in' : 'free',
        entered_at: nowISO,
        left_at   : null,
      })
    })

    // --- Diagnostics (Step 1 continued) ---
    try {
      console.log('[diag save:staysBuilt]', stays.map(s => ({ cast: s.cast.id, stay_type: s.stay_type })))
    } catch(e){ /* noop */ }

    const table_id = tableId.value ?? (bill.value?.table?.id ?? bill.value?.table ?? null)
    const optimisticId = isNewBill ? -Date.now() : bill.value.id
    const optimisticBill = {
      id: optimisticId,
      table: { id: table_id, number: bill.value?.table?.number ?? null, store: bill.value?.table?.store ?? null },
      customers: bill.value?.customers || [],
      stays,
      opened_at: bill.value?.opened_at || nowISO,
      expected_out: bill.value?.expected_out || null,
      pax: pax.value ?? bill.value?.pax ?? null,
      subtotal: bill.value?.subtotal ?? 0,
      closed_at: null
    }

    try {
      console.log('[diag save:optimisticBill]', {
        id: optimisticBill.id,
        stays: optimisticBill.stays.map(s => ({ cast: s.cast.id, stay_type: s.stay_type })),
        nominated_next: [...mainIds.value],
        inhouse_next: [...inhouseIds.value],
        free_next: [...freeIds.value],
        dohan_next: [...dohanIds.value],
      })
    } catch(e){ /* noop */ }

    // UIへ即時反映（upsert）
    const i = billsStore.list.findIndex(b => Number(b.id) === Number(optimisticId))
    if (i >= 0) billsStore.list[i] = optimisticBill
    else billsStore.list.unshift(optimisticBill)

    // キュー投入（裏で確定）
    const memoStr = ''  // 必要ならモーダル側から受け取って渡す

    const commonTimePayload = { opened_at: optimisticBill.opened_at, expected_out: optimisticBill.expected_out }

    if (isNewBill){
      enqueue('createBill', { tempId: optimisticId, table_id, ...commonTimePayload, memo: memoStr })
      enqueue('updateBillTable', { id: optimisticId, table_id })
      // create 時に opened_at/expected_out が無視されるケースへの保険
      enqueue('patchBill', { id: optimisticId, payload: commonTimePayload })
    }else{
      const currentTableId = bill.value.table?.id ?? bill.value.table ?? null
      if (table_id !== currentTableId) enqueue('updateBillTable', { id: optimisticId, table_id })
      // 既存伝票でも保存時に開始/終了を必ず送る（他パネル保存で現在時刻に戻るのを防ぐ）
      enqueue('patchBill', { id: optimisticId, payload: { ...commonTimePayload, memo: memoStr } })
    }

    if ((bill.value?.customers?.length ?? 0) > 0){
      enqueue('updateBillCustomers', { id: optimisticId, customer_ids: bill.value.customers })
    }

    enqueue('updateBillCasts', {
      billId: optimisticId,
      nomIds: [...(mainIds.value||[])],
      inIds : [...(inhouseIds.value||[])],
      freeIds: (freeIds.value||[]).filter(id => !mainIds.value.includes(id) && !dohanIds.value.includes(id)),
      dohanIds: [...(dohanIds.value||[])],
    })
    try {
      console.log('[diag save:enqueue updateBillCasts]', {
        billId: optimisticId,
        nomIds: [...(mainIds.value||[])],
        inIds: [...(inhouseIds.value||[])],
        freeIds: [...(freeIds.value||[])],
        dohanIds: [...(dohanIds.value||[])],
      })
    } catch(e){ /* noop */ }

    for (const it of pending.value || []){
      enqueue('addBillItem', { 
        id: optimisticId, 
        item: { 
          item_master: it.master_id, 
          qty: it.qty, 
          served_by_cast_id: it.cast_id ?? undefined,
          customer_id: it.customer_id ?? undefined
        } 
      })
    }
    pending.value = []

    enqueue('reconcile', { id: optimisticId })
    try { console.log('[diag save:enqueue reconcile]', { billId: optimisticId }) } catch(e){ /* noop */ }

    return optimisticBill
  }


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
    servedByCastId, selectedCustomerId, addPending,  // 【フェーズ3】selectedCustomerId を追加
    pending,  // 既存をここでも返しておく（保存で使う）

    // SP: 顧客インライン検索
    custQuery, custResults, custLoading, searchCustomers, resetCustomerSearch, pickCustomerInline,
    selectedCustomer,

    save,
  }
}
