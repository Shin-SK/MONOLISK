# Payroll Snapshot 方針A 適用レポート（Bill 136）

- 作成日: 2026-02-26
- 対象実装: `billing/payroll/snapshot.py`
- 対象 Bill: `id=136`
- 目的: by_cast を「支払の真実」に揃え、items.payroll_effects との母集団ズレを解消する

---

## 実施内容（最小変更）

### 1) by_cast 生成順の変更

`build_payroll_snapshot` で `items_info` を先に生成し、その結果を `_build_by_cast(...)` に渡すよう変更。

- 変更前: `by_cast -> items_info -> totals`
- 変更後: `items_info -> by_cast -> totals`

### 2) by_cast の母集団を統一（SSOT）

`_build_by_cast` の対象 cast を以下の和集合に変更:

- `result.cast_payouts` の cast_id
- `items_info[].payroll_effects[].cast_id`

これにより、items 側に登場する cast が by_cast から欠落しないようにした。

### 3) by_cast.amount の定義

cast ごとの最終支払を以下で算出:

- `amount = payout_amount + item_back_amount`

ここで:

- `payout_amount`: `cast_payouts` 由来（なければ0）
- `item_back_amount`: `items_info.payroll_effects(type=item_back)` 合算

### 4) breakdown.item_back の整合化

`_build_by_cast` 内で `items_info` から cast別 item_back detail を再構築し、`by_cast.breakdown[type=item_back]` に反映。

- これにより `items.payroll_effects` と `by_cast.breakdown.item_back` が同じ根拠データを共有。

### 5) adjustment の縮小

`adjustment = amount - (item_back + nomination_pool + dohan_pool)` として算出。

- 母集団ズレが解消されたため、Bill136では `adjustment=0` を確認。

---

## 検証手順

VSCode ターミナルで以下を実行:

```bash
/Users/koyanagikokoro/Dropbox/PRODUCTS/MONOLISK/venv/bin/python manage.py shell < /tmp/payroll_check_136.py
```

---

## 検証結果（Bill 136）

### totals

```python
{
  'dohan_total': 0,
  'grand_total': 633840,
  'hourly_total': 0,
  'item_total': 208000,
  'labor_total': 468000,
  'nomination_total': 260000,
  'service_charge': 52820,
  'subtotal': 528200,
  'tax': 52820
}
```

### by_cast summary

```python
{'cast_id': 68, 'stay_type': 'nom', 'amount': 104000}
{'cast_id': 72, 'stay_type': 'nom', 'amount': 364000}
```

### 主要チェック

- by_cast に 68/72 の両方が出る: ✅
- `sum(by_cast.breakdown.item_back) == totals.item_total`
  - `208000 == 208000` → ✅
- `sum(by_cast.amount) == totals.labor_total`
  - `468000 == 468000` → ✅
- `sum(items.payroll_effects.amount) == totals.item_total`
  - `208000 == 208000` → ✅
- `sum(adjustment) == 0` → ✅

### rate 型

- by_cast detail / items payroll_effects ともに `rate_type='str'` を維持。

### nomination 混入

- item_back item_id: `[232, 233]`
- `is_nomination=True` item_id: `[230, 231]`
- 共通集合: `[]` → ✅ 混入なし

---

## 結論

方針A（by_cast=支払の真実）に沿って、母集団不一致を構造的に解消できた。

- 以前の問題（itemsに出るcastがby_castに出ない）を解消
- item_back の整合性が回復
- 母集団ズレ由来の adjustment 常態化を解消（Bill136で0確認）

今回の変更は `billing/payroll/snapshot.py` のみ。DB更新は実施していない。
