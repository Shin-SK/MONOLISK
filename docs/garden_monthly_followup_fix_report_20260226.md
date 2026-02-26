# Garden 月次制度 フォローアップ修正レポート（2026-02-26）

## 依頼内容
- 仕上げの微修正
  1. `garden.py` の `dohan_count` 集計を簡素化
  2. ドキュメント重複の確認
- 最終チェック実行
  - `python3 manage.py check`
  - `python3 manage.py makemigrations --check --dry-run`
  - `python3 manage.py migrate`
- `BaseEngine.finalize_payroll_line` の存在確認

## 変更内容

### 1) `billing/payroll/engines/stores/garden.py`
- `calculate_garden_stats()` の `dohan_count` を以下へ変更
  - 変更前: `BillCastStay` に対する別クエリで `distinct().count()`
  - 変更後: 既存の `dohan_bill_ids_qs.count()` を利用
- 目的: クエリ冗長を1本削減（動作は同等）

## 確認結果

### 2) ドキュメント重複
- `garden_monthly_system.md` は1ファイルのみ存在
  - `doc/garden_monthly_system.md`
- 同名重複はなし

### 3) BaseEngine フック
- `billing/payroll/engines/base.py` に `finalize_payroll_line(...)` が存在することを確認
- GardenEngine 側の override 呼び出し前提は満たしている

## コマンド実行結果

### `python3 manage.py check`
- 結果: `System check identified no issues (0 silenced).`
- 備考: `dj_rest_auth` の deprecation warning は表示されるが、今回変更範囲外

### `python3 manage.py makemigrations --check --dry-run`
- 結果: `No changes detected`

### `python3 manage.py migrate`
- 結果: 未適用だったマイグレーションが適用された
  - `billing.0128_garden_monthly_fields ... OK`

## 最終状態
- 仕上げ修正（クエリ簡素化）は反映済み
- Garden関連の最終チェックは実行済み
- `BaseEngine.finalize_payroll_line` は存在確認済み
- ドキュメント同名重複はなし
