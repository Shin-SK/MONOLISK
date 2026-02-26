# Bill 136 給与スナップショット検証レポート

- 作成日: 2026-02-26
- 対象: `Bill(id=136)`
- 対象実装: `billing/payroll/snapshot.py`
- 目的: 
  - `build_payroll_snapshot` が実データで実行可能であることの確認
  - 期待値照合に必要な数値観測点の取得
- 制約遵守:
  - コード変更なし
  - 新規永続ファイル追加なし（`/tmp` に一時スクリプトのみ）
  - DB更新/保存なし（参照のみ）

---

## 実行方法（VSCode ターミナル）

1. 一時検証スクリプト作成
   - `/tmp/payroll_check_136.py`
2. 実行

```bash
/Users/koyanagikokoro/Dropbox/PRODUCTS/MONOLISK/venv/bin/python manage.py shell < /tmp/payroll_check_136.py
```

---

## 実行結果サマリ

- `Bill id=136 loaded`
- `store=エクストラ[参考店]`
- `build_payroll_snapshot(bill)` 実行成功

### totals

```python
{
  'dohan_total': 0,
  'grand_total': 633840,
  'hourly_total': 0,
  'item_total': 208000,
  'labor_total': 260000,
  'nomination_total': 260000,
  'service_charge': 52820,
  'subtotal': 528200,
  'tax': 52820
}
```

### by_cast（cast_id / stay_type / amount）

```python
{'cast_id': 72, 'stay_type': 'nom', 'amount': 260000}
```

### by_cast breakdown.item_back detail（抜粋）

```python
{'cast_id': 72, 'item_id': 232, 'qty': 1, 'unit_price': 195000, 'subtotal': 195000, 'rate_str': '0.20', 'rate_decimal': '0.20', 'basis': 'subtotal', 'amount': 39000, 'rate_type': 'str'}
{'cast_id': 72, 'item_id': 233, 'qty': 1, 'unit_price': 325000, 'subtotal': 325000, 'rate_str': '0.20', 'rate_decimal': '0.20', 'basis': 'subtotal', 'amount': 65000, 'rate_type': 'str'}
```

### items.bill_item_id ごとの payroll_effects（抜粋）

```python
{'bill_item_id': 225, 'payroll_effects': []}
{'bill_item_id': 232, 'cast_id': 72, 'amount': 39000, 'basis.rate_str': '0.20', 'basis.rate_decimal': '0.20', 'basis.basis_type': 'subtotal', 'basis.calculation': 'subtotal * rate / n', 'basis.rate_type': 'str'}
{'bill_item_id': 232, 'cast_id': 68, 'amount': 39000, 'basis.rate_str': '0.20', 'basis.rate_decimal': '0.20', 'basis.basis_type': 'subtotal', 'basis.calculation': 'subtotal * rate / n', 'basis.rate_type': 'str'}
{'bill_item_id': 233, 'cast_id': 72, 'amount': 65000, 'basis.rate_str': '0.20', 'basis.rate_decimal': '0.20', 'basis.basis_type': 'subtotal', 'basis.calculation': 'subtotal * rate / n', 'basis.rate_type': 'str'}
{'bill_item_id': 233, 'cast_id': 68, 'amount': 65000, 'basis.rate_str': '0.20', 'basis.rate_decimal': '0.20', 'basis.basis_type': 'subtotal', 'basis.calculation': 'subtotal * rate / n', 'basis.rate_type': 'str'}
```

---

## 確認ポイントの判定

### 1) rate が str か（型確認）

- by_cast detail 側: `rate_type = 'str'`
- items payroll_effects 側: `basis.rate_type = 'str'`

✅ 両方とも `str` を確認。

### 2) nomination item の item_back 混入有無

- item_back に出現した item_id: `[232, 233]`
- `Bill.items(is_nomination=True)` の item_id: `[230, 231]`
- 共通集合: `[]`

✅ 混入なし。

### 3) 整合性チェック

- `labor_total(totals) == sum(by_cast.amount)`
  - `260000 == 260000` → ✅ True
- `item_total(totals) == sum(items.payroll_effects.amount)`
  - `208000 == 208000` → ✅ True
- `sum(item_back breakdown) == item_total(totals)`
  - `104000 == 208000` → ❌ False
- `sum(nomination_pool breakdown) == nomination_total(totals)`
  - `260000 == 260000` → ✅ True
- `sum(dohan_pool breakdown) == dohan_total(totals)`
  - `0 == 0` → ✅ True
- `sum(adjustment)`
  - `-104000`

---

## 所見（今回確認できた事実）

- スナップショット計算自体は正常に実行され、観測点は取得できた。
- `rate` は期待通り文字列として出力されている。
- nomination item の item_back 混入は確認されなかった。
- 一方で、`by_cast.breakdown.item_back` 合計と `totals.item_total` に差分（104000）があり、`adjustment=-104000` が計上されている。
  - 出力上、`items.payroll_effects` には cast_id `68` と `72` の両方が現れるが、`by_cast` は cast_id `72` のみ。
  - この差分が breakdown 側との不一致に寄与している可能性が高い（追加調査対象）。

---

## 次の調査候補（任意）

- Bill 136 の `stays(left_at is null)` に cast 68 が含まれているか確認。
- `result.cast_payouts` の cast_id 一覧と `items.payroll_effects.cast_id` 一覧の差分確認。
- `by_cast` 構築対象（cast_payouts起点）と item_back detail 構築対象のキャスト集合差を明示比較。
