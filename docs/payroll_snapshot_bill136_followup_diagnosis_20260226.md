# Bill 136 payroll snapshot 追加診断レポート

- 作成日: 2026-02-26
- 対象: Bill id=136
- 目的: items.payroll_effects に cast_id=68 が出る一方で by_cast に出ない理由を、コード変更なしで特定
- 実施方式: VSCode ターミナルで `python manage.py shell < /tmp/payroll_check_136_followup.py`
- 制約: DB更新なし / 既存コード変更なし

---

## 追加チェック項目と結果

### 1) active stays（left_at is null）

```python
{'cast_id': 68, 'stay_type': 'nom'}
{'cast_id': 72, 'stay_type': 'nom'}
```

- cast 68 は「現員」に存在している（幽霊キャストではない）。

### 2) BillCalculator.cast_payouts（by_cast の母集団）

```python
{'cast_id': 72, 'amount': 260000}
```

- payout 対象は cast 72 のみ。

### 3) item 232/233 の served_by 情報

```python
{'item_id': 232, 'served_by_cast_id': 72, 'served_by_casts': [68, 72], 'is_nomination': False}
{'item_id': 233, 'served_by_cast_id': 68, 'served_by_casts': [68, 72], 'is_nomination': False}
```

- 両 item とも M2M served_by_casts に 68/72 の両方が含まれる。

### 4) 集合差分（payroll_effects.cast_id vs cast_payouts.cast_id）

```python
payroll_effect_cast_ids: [68, 72]
cast_payout_cast_ids: [72]
effects_minus_payouts: [68]
payouts_minus_effects: []
```

- payroll_effects 側にのみ cast 68 が存在。

---

## 結論

- 検証は正しく実行できており、観測結果は一貫している。
- 現象の本体は以下の「母集団不一致」:
  - item_back の配分母集団: `served_by_casts`（68,72）
  - by_cast の集計母集団: `result.cast_payouts`（72のみ）
- そのため cast 68 に配分された item_back 分が by_cast に載らず、差分が `adjustment` に落ちる挙動になる。

---

## 判定メモ

- 以前の「幽霊キャスト混入」仮説は今回データでは該当しない（68 は active stay に存在）。
- 今回は「仕様/設計上の母集団ズレ」が直接原因として確認できた。
- 実運用上は、adjustment 常態化・説明困難・dirty 判定ノイズにつながるため、方針統一（配分対象と支払対象の整合）が必要。
