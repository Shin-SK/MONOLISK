# Garden 暫定ランクAPI 実装報告書

**日付**: 2026-02-26
**対象**: `GET /api/billing/payroll/status/`

## 変更ファイル (2ファイル)

### 1. billing/views.py
- `PayrollStatusView` (APIView) を末尾に追加
- 認証: `IsAuthenticated` (TokenAuth)
- Store-Locked: `X-Store-Id` ヘッダから取得 (既存 `_get_store_id_from_header` を再利用)
- 期間計算: 既存 `get_default_payroll_period(store, today)` を再利用
- 集計: `calculate_garden_stats(store, cast_id, period_start, today)` を呼び出し (重複実装なし)
- Garden以外の店舗: `{"enabled": false}` を返却 (エラーにならない)
- cast_id: `request.user` + `store_id` で Cast を検索。見つからなければ 404

### 2. billing/urls.py
- `PayrollStatusView` を import に追加
- `path("payroll/status/", ...)` を payroll セクションに追加

## API仕様

**エンドポイント**: `GET /api/billing/payroll/status/`
**ヘッダ**: `Authorization: Token <token>`, `X-Store-Id: <store_id>`

### レスポンス (Garden店)
```json
{
  "period_start": "YYYY-MM-DD",
  "period_end": "YYYY-MM-DD",
  "as_of": "YYYY-MM-DD",
  "cast_id": 123,
  "sales_total": 0,
  "nom_count": 0,
  "dohan_count": 0,
  "dohan_sales_total": 0,
  "points": 0,
  "rank": "D",
  "hourly": 2000,
  "slide_rate": 0,
  "slide_back": 0,
  "dohan_back": 0,
  "b_back": 0,
  "monthly_back": 0
}
```

### レスポンス (Garden以外)
```json
{"enabled": false}
```

### エラーケース
- X-Store-Id なし: **400** `{"detail": "X-Store-Id header is required"}`
- store_id が存在しない: 404
- request.user に紐づく Cast がない: 404

## 仕上げ修正 (2回目)

- `_get_store_id_from_header()` の ValueError を try/except で捕捉し 400 を返すように修正
- billing/urls.py のルーティング確認済み (L83: `path("payroll/status/", ...)`)

## 検証

- `python3 manage.py check` -- **OK** (0 issues)
- garden.py への変更なし (calculate_garden_stats をそのまま利用)
- 未使用 import の追加なし
- Store-Locked 原則を遵守 (クエリで store 指定せず、ヘッダから取得)
