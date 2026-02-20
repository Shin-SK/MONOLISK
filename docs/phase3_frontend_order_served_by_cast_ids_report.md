# Phase 3 Frontend Report: 注文モーダル 担当ピル複数選択対応

**実装完了日**: 2026年2月20日

## 実装概要

注文モーダルで担当キャストを複数選択できるようにし、注文送信時に `served_by_cast_ids` をサーバへ渡すように変更しました。
既存互換として `served_by_cast_id`（先頭ID）も同時送信します。

---

## 変更内容

### 1) 注文UI（担当ピル）を複数選択化

- 対象: [frontend/src/components/panel/OrderPanel.vue](frontend/src/components/panel/OrderPanel.vue)
- 対象: [frontend/src/components/spPanel/OrderPanelSP.vue](frontend/src/components/spPanel/OrderPanelSP.vue)

実装:
- `servedByCastIds`（配列）props を追加
- `update:servedByCastIds` emit を追加
- 担当ピルをトグル選択化（入っていたら外す / なければ追加）
- 「未指定」で空配列 `[]` にクリア
- 追加時の emit を配列化
  - `addPending(masterId, qty, castIds, customerId)`
- カート表示は複数担当を「A＋B」形式で表示

### 2) BillModalSP 側の pending 反映

- 対象: [frontend/src/components/BillModalSP.vue](frontend/src/components/BillModalSP.vue)

実装:
- `v-model:served-by-cast-ids` 受け取りを追加
- `@addPending` で pending に複数担当を保存
  - `cast_ids: ids`
  - `cast_id: ids[0] || null`（互換）
- 既存の単一担当監視が発火した場合も、`cast_ids` が空なら `[cast_id]` で補完

### 3) BillModalPC 側の pending/placeOrder 反映

- 対象: [frontend/src/components/BillModalPC.vue](frontend/src/components/BillModalPC.vue)

実装:
- `servedByCastIds` 状態を追加
- `OrderPanelSP` へ `served-by-cast-ids` を受け渡し
- `onAddPending` を配列入力対応
  - `cast_ids` 保存
  - `cast_id` は先頭で互換保存
- `save()` 内 `addBillItem` payload を変更
  - `served_by_cast_ids: castIds`
  - `served_by_cast_id: castIds[0]`（互換）

### 4) SP保存フロー（useBillEditor）で payload 対応

- 対象: [frontend/src/composables/useBillEditor.js](frontend/src/composables/useBillEditor.js)

実装:
- `servedByCastIds` 状態を追加
- `addPending()` を配列対応
  - pending に `cast_ids` と `cast_id`（先頭）を保存
- `save()` の `enqueue('addBillItem')` payload を変更
  - `served_by_cast_ids` を送信
  - `served_by_cast_id` も先頭で送信

---

## 送信仕様（最終）

`addBillItem` 送信時:

- `item_master`
- `qty`
- `served_by_cast_ids: [id1, id2, ...]`
- `served_by_cast_id: id1`（配列先頭、互換）
- `customer_id`（指定時のみ）

---

## 確認結果

### 静的チェック

- 編集ファイルのエラー確認: 問題なし

### ビルド確認

実行コマンド:

- `REDIRECTS_PROFILE=stg npm --prefix frontend run build`

結果:

- Vite build 成功（compile OK）

---

## 手動確認チェックリスト（今日のゴール）

1. 注文モーダルで担当ピルが複数選択できる
2. 「未指定」で担当配列が空になる
3. 注文時の Network payload に `served_by_cast_ids` が含まれる
4. 同 payload に `served_by_cast_id`（先頭）も含まれる
5. 取得レスポンスに `served_by_cast_ids` が返る
6. 画面更新後も担当が保持される

---

## 影響範囲

- 変更あり: 注文モーダル（SP/PC）の担当選択UI
- 変更あり: pending → addBillItem 送信ペイロード
- 非変更: 会計・給与計算ロジック
