# Phase2: 複数テーブル（M2M tables）実装完了報告

**実装日**: 2026年2月12日

## 目的

Bill の複数テーブル（M2M tables）を"必ず"機能させる。フロントが `table_ids` を送れば確実に M2M が保存され、レスポンスの `table_atoms` / `table_atom_ids` / `table_label` が正しく埋まる。

## 実装内容

### バックエンド（Django + DRF）

#### 1. `billing/serializers.py` - BillSerializer

##### `_sync_tables` メソッドを追加（`_assign_tables` を置き換え）

```python
def _sync_tables(self, bill, validated_data):
    """
    目的: Bill.tables(M2M) を正にして、legacy FK(bill.table) と同期する。
    入力優先順位:
      1) table_ids（新）
      2) table / table_id（旧）
      3) 何も来ない場合は変更しない
    """
```

**処理内容**:
- **優先順位1**: `table_ids`（新）→ M2M を設定し、legacy FK の先頭に同期
- **優先順位2**: `table` / `table_id`（旧）→ M2M が空なら追加、legacy FK も同期
- **空配列の場合**: M2M をクリアし、legacy FK も `None` に

##### `create` メソッドを修正

- `table_ids` と legacy フィールド（`table`, `table_id`）を保存
- Bill 作成後に `_sync_tables` を呼び出し
- legacy 入力（`table`/`table_id`）も確実に M2M に反映

##### `update` メソッドを修正

- 同様に `table_ids` と legacy フィールドを保存
- Bill 更新後に `_sync_tables` を呼び出し
- 既存の旧 UI や集計コードが壊れないように legacy FK と同期

##### Legacy FK 同期の仕組み

- M2M で複数テーブルを選択した場合、`bill.table` は先頭の ID を保持
- 旧式の API 呼び出しでも M2M に確実に反映される
- 単卓→複数卓、複数卓→単卓の切り替えも安全に動作

---

### フロントエンド（Vue）

#### 1. `frontend/src/api.js` - API 関数

##### `toTableIds` ヘルパー関数を追加

```javascript
const toTableIds = (p = {}) => {
  if (Array.isArray(p.tableIds) && p.tableIds.length) return p.tableIds.map(Number)
  if (Array.isArray(p.table_ids) && p.table_ids.length) return p.table_ids.map(Number)
  if (Array.isArray(p.table_atom_ids) && p.table_atom_ids.length) return p.table_atom_ids.map(Number)

  if (p.table != null) {
    if (typeof p.table === 'number') return [Number(p.table)]
    if (typeof p.table === 'object' && p.table.id != null) return [Number(p.table.id)]
  }
  if (p.table_id != null) return [Number(p.table_id)]
  return []
}
```

**目的**: 新旧の入力形式を統一して `table_ids` 配列に変換

##### `createBill` を修正

```javascript
export const createBill = (arg = {}) => {
  const payload = (typeof arg === 'number') ? { table_id: arg } : { ...arg }
  const table_ids = toTableIds(payload)

  const body = {
    table_ids, // ★必須（単卓でも配列）
    ...(payload.opened_at ? { opened_at: payload.opened_at } : {}),  // ★ null送らない
    ...(payload.expected_out !== undefined ? { expected_out: payload.expected_out } : {}),
    ...(payload.pax != null ? { pax: payload.pax } : {}),
    ...(payload.apply_service_charge !== undefined ? { apply_service_charge: !!payload.apply_service_charge } : {}),
    ...(payload.apply_tax !== undefined ? { apply_tax: !!payload.apply_tax } : {}),
    ...(payload.memo != null ? { memo: String(payload.memo) } : {}),
  }
  return api.post('billing/bills/', body).then(r => r.data)
}
```

**変更点**:
- `table_id` → `table_ids` に統一（単卓でも配列）
- `opened_at` は値がある時だけ送信（null 禁止）

##### `patchBill` を修正

```javascript
export const patchBill = (id, payload = {}) => {
  const table_ids = toTableIds(payload)
  const hasTableIdsIntent =
    Object.prototype.hasOwnProperty.call(payload, 'tableIds') ||
    Object.prototype.hasOwnProperty.call(payload, 'table_ids') ||
    Object.prototype.hasOwnProperty.call(payload, 'table_atom_ids') ||
    Object.prototype.hasOwnProperty.call(payload, 'table') ||
    Object.prototype.hasOwnProperty.call(payload, 'table_id')

  const body = {
    ...(hasTableIdsIntent ? { table_ids } : {}), // ★空配列も送れる
    ...(payload.opened_at ? { opened_at: payload.opened_at } : {}), // ★null送らない
    ...(payload.expected_out !== undefined ? { expected_out: payload.expected_out } : {}),
    ...(payload.pax !== undefined ? { pax: payload.pax } : {}),
    ...(payload.apply_service_charge !== undefined ? { apply_service_charge: !!payload.apply_service_charge } : {}),
    ...(payload.apply_tax !== undefined ? { apply_tax: !!payload.apply_tax } : {}),
    ...(payload.memo !== undefined ? { memo: payload.memo } : {}),
    // その他のフィールドも通す（manual_discounts 等）
    ...Object.keys(payload)
      .filter(k => !['tableIds', 'table_ids', 'table_atom_ids', 'table', 'table_id', 'opened_at', 'expected_out', 'pax', 'apply_service_charge', 'apply_tax', 'memo'].includes(k))
      .reduce((acc, k) => ({ ...acc, [k]: payload[k] }), {}),
  }

  return api.patch(`billing/bills/${id}/`, body).then(r => r.data)
}
```

**変更点**:
- `table_ids` を優先、legacy フィールドは toTableIds で吸収
- `opened_at` の null 送信を防止
- `tableIds`（UI側）も toTableIds が吸収
- PATCH 時に空配列のクリアが可能（intent 判定あり）

#### 2. `frontend/src/components/BillModalSP.vue` - SP版モーダル

##### `ensureBillId` を修正

```javascript
async function ensureBillId () {
  if (props.bill?.id) return props.bill.id

  // tableIds（複数選択）が優先、なければ単一の tableId を配列化
  let tableIdsPayload = []
  
  if (tableIds.value && tableIds.value.length > 0) {
    // 複数テーブル選択がある場合
    tableIdsPayload = tableIds.value.map(Number)
  } else {
    // 単一テーブル選択
    const tableId = /* ... 既存の導出ロジック ... */
    if (!tableId) { alert('テーブルが未選択です'); throw new Error('no table') }
    tableIdsPayload = [tableId]
  }

  const req = {
    table_ids: tableIdsPayload,  // ★table_ids で送る（単卓でも配列）
    ...(props.bill?.opened_at ? { opened_at: props.bill.opened_at } : {}),
    expected_out: props.bill?.expected_out ?? null,
    pax: paxPayload,
    apply_service_charge: props.bill?.apply_service_charge !== false,
    apply_tax: props.bill?.apply_tax !== false,
  }
  const b = await createBill(req)
  // ...
}
```

**変更点**:
- 複数選択 `tableIds` が優先、なければ単一 `tableId` を配列化
- `table_ids` で必ず送信

#### 3. `frontend/src/components/BillModalPC.vue` - PC版モーダル

##### `save` メソッドを修正

```javascript
async function save () {
  // ...
  if (wasNew) {
    const payload = {
      tableIds: form.table_ids && form.table_ids.length > 0 ? form.table_ids : [],
      memo: String(memoRef.value || ''),
      apply_service_charge: applyServiceCharge.value,
      apply_tax: applyTax.value,
    }
    // opened_at は値がある時だけ送る
    if (form.opened_at) {
      payload.opened_at = dayjs(form.opened_at).toISOString()
    }
    if (form.expected_out) {
      payload.expected_out = dayjs(form.expected_out).toISOString()
    }
    const created = await createBill(payload)
    // ...
  } else {
    // 既存更新
    const patchPayload = {
      memo: String(memoRef.value || ''),
      apply_service_charge: applyServiceCharge.value,
      apply_tax: applyTax.value,
    }
    
    if (form.opened_at) {
      patchPayload.opened_at = dayjs(form.opened_at).toISOString()
    }
    if (form.expected_out) {
      patchPayload.expected_out = dayjs(form.expected_out).toISOString()
    }
    
    await patchBill(billId, patchPayload)
  }
}
```

**変更点**:
- `opened_at` / `expected_out` は値がある時だけペイロードに含める
- null を送信しない

---

## 動作確認項目

### バックエンド

✅ **POST `/api/billing/bills/` に `{"table_ids":[72,73]}` を送信**
   - レスポンスで `table_atom_ids` が `[72,73]` で返る
   - `table_label` が `"AB"` 等で返る（空にならない）
   - legacy FK `table` は `72` に設定される

✅ **POST に旧式で `{"table":72}` を送信**
   - レスポンスで `table_atom_ids` が `[72]` で返る
   - M2M と legacy FK の両方が同期される

✅ **PATCH `/api/billing/bills/{id}/` に `{"table_ids":[72,73]}` を送信**
   - M2M が更新される
   - legacy FK も先頭の ID に同期

### フロントエンド

✅ **新規作成後のレスポンスで `table_atom_ids` が空にならない**

✅ **複数卓で作成したら `table_atom_ids` が複数になる**

✅ **フロントの画面が `table_label` を表示できる（空のままにならない）**

✅ **POST 400 エラー（opened_at: null）が発生しない**

---

## 追加の修正（txQueue 404 対応）

### `frontend/src/utils/txQueue.js`

404 エラー時はキューから破棄するように修正：

```javascript
catch(e){
  try { console.warn('[diag txQueue:taskError]', { kind: task.kind, payload: task.payload, error: e?.message }) } catch(_){ /* noop */ }
  
  // 404 の場合は破棄（DBリセット/古いID残骸）
  const status = e?.response?.status
  if (status === 404) {
    console.warn('[txQueue] 404 detected, discarding task:', task.kind, task.payload)
    queue.splice(idx, 1)
    save(queue)
    continue
  }
  
  task.tries = (task.tries||0)+1
  // ...
}
```

**目的**: DBリセットや古いIDでの 404 エラーループを防止

---

## まとめ

### 実装済み機能

1. **M2M テーブルの完全対応**
   - フロントから `table_ids` を送信すると、M2M と legacy FK の両方が同期
   - 旧式の `table` / `table_id` も受け入れ、M2M に自動反映

2. **opened_at の null 送信防止**
   - 値がある時だけ送信、バックエンドの allow_null=False に対応

3. **404 エラーのループ防止**
   - txQueue で 404 エラーを検知して自動破棄

### 互換性

- **旧 UI との共存**: legacy FK（`bill.table`）を維持しているため、既存の集計や旧 UI も動作
- **段階的移行**: 新規作成は `table_ids` で、既存データは徐々に M2M に移行可能

### 今後の拡張

- 既存の旧データ（`table_atoms` が空）を DB 側でバックフィルする管理コマンドの追加
- legacy FK の完全廃止（Phase 3）

---

**実装完了**: 2026年2月12日
**実装者**: GitHub Copilot (GPT-5.2-Codex)
