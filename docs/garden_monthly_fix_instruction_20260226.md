# Garden月次制度 修正指示書（2026-02-26）

## 目的
Garden店の月次ランク制度ロジックを、確定仕様に合わせて修正する。

## 反映済みファイル
- `billing/payroll/engines/stores/garden.py`
- `billing/exports/payroll_run_csv.py`
- `doc/garden_monthly_system.md`

## 反映内容

### 1) `billing/payroll/engines/stores/garden.py`
- ポイント式を仕様へ修正
  - 本指名: 2pt → 1pt
  - 同伴: 2pt（維持）
- ランク境界を仕様へ修正
  - A: `>=60`, B: `>=30`, C: `>=1`, D: `0`
- 小計スライドバック対象を A のみに修正
- 売上集計を `price * qty` の ORM集計に統一
  - `ExpressionWrapper(F("price") * F("qty"), output_field=IntegerField())`
- 同伴本数を `distinct().count()` で DB集計
- `slide_rate` を算出結果に追加（Aのみ有効）
- `finalize_payroll_line` の数値処理を安全化
  - `worked_min`, `hourly`, `commission`, `monthly_back` を `int()` 経由で計算

### 2) `billing/exports/payroll_run_csv.py`
- `PayrollRunLine.objects.bulk_create(lines)` の戻り値を再代入
  - `lines = PayrollRunLine.objects.bulk_create(lines)`
- finalize 後の更新対象が保存済みインスタンスになることを保証

### 3) `doc/garden_monthly_system.md`
- 仕様書を「確定版」に更新
  - ポイント、ランク境界、Aのみスライド、B 5%固定、集計定義、テスト観点を整理

## 今回見送ったもの
- `billing/models.py` の `garden_snapshot` / `label` 追加
- `billing/migrations/0128_garden_monthly_fields.py` の作成

理由: 現在のコードベースで両フィールドは既に存在し、`makemigrations --check --dry-run` でも差分なしを確認済み。

## 検証結果

### 静的チェック
- `garden.py` / `payroll_run_csv.py`: エラーなし（Problems API）

### Djangoチェック
- `python manage.py check` → `System check identified no issues`
- `python manage.py makemigrations --check --dry-run` → `No changes detected`

※ いずれも `dj_rest_auth` の deprecation warning は表示されるが、今回変更範囲とは無関係。

## 追加確認（任意）
以下を実行して Garden店の給与CSVを実データで再確認:

```bash
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
```

必要に応じて本番前に:

```bash
python3 manage.py migrate
```

（今回はマイグレーション差分なしのため、適用対象はなし）
